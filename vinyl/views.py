import difflib
import itertools
import hashlib
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count
from .models import Vinyl, Artist, RecordLabel, VinylGenre
from .forms import VinylForm
from .search import search_q

ITUNES_HOST = 'itunes.apple.com'
DEEZER_HOST = 'api.deezer.com'
# Domini da cui è consentito scaricare le copertine (anti-SSRF)
# Solo https, host = sottodomini alfanumerici di mzstatic.com / dzcdn.net, niente userinfo/porta
COVER_URL_RE = re.compile(r'https://[a-z0-9-]+(\.[a-z0-9-]+)*\.(mzstatic\.com|dzcdn\.net)/[^\s#]*')
MAX_DESCRIPTION_LENGTH = 500


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Blocca i redirect: un host consentito non può rimandare verso host interni (anti-SSRF)."""
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _http_get_json(url, timeout=6):
    """GET JSON con cache (EXTERNAL_API_CACHE_SECONDS). Gli errori non si cachano; se la cache è giù si va diretti."""
    key = 'extapi:' + hashlib.sha256(url.encode()).hexdigest()
    try:
        cached = cache.get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached
    req = urllib.request.Request(url, headers={'User-Agent': 'PersonalLibraryApp/1.0'})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception:
        return None
    try:
        cache.set(key, data, settings.EXTERNAL_API_CACHE_SECONDS)
    except Exception:
        pass
    return data


def _run_sources_parallel(tasks, timeout=8):
    """Interroga le fonti in parallelo; chi non risponde entro il timeout viene ignorato.

    I risultati vengono alternati (round-robin) tra le fonti anziché concatenati:
    altrimenti, se una fonte restituisce molti candidati "completi" (con copertina/anno),
    questi riempiono l'intera classifica prima che i risultati di un'altra fonte -
    magari più pertinenti - abbiano la possibilità di comparire.
    """
    executor = ThreadPoolExecutor(max_workers=len(tasks))
    futures = [executor.submit(task) for task in tasks]
    per_source = []
    for future in futures:
        try:
            per_source.append(future.result(timeout=timeout))
        except Exception:
            per_source.append([])
    executor.shutdown(wait=False, cancel_futures=True)

    results = []
    for interleaved in itertools.zip_longest(*per_source):
        for item in interleaved:
            if item is not None:
                results.append(item)
    return results


def _similarity(a, b):
    return difflib.SequenceMatcher(None, (a or '').lower(), (b or '').lower()).ratio()


def _get_or_create_artist(name):
    name = name.strip()
    if not name:
        return None
    artist, _ = Artist.objects.get_or_create(name=name[:200])
    return artist


def _get_or_create_label(name):
    name = name.strip()
    if not name:
        return None
    label, _ = RecordLabel.objects.get_or_create(name=name[:200])
    return label


def _get_or_create_genres(names):
    genres = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        genre, _ = VinylGenre.objects.get_or_create(name=name[:100])
        genres.append(genre)
    return genres


def _search_vinyl_info_itunes(title, artist):
    term = f'{artist} {title}'.strip()
    search_url = f'https://{ITUNES_HOST}/search?' + urllib.parse.urlencode({
        'term': term,
        'entity': 'album',
        'limit': 15,
    })
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for item in data.get('results', []):
        artwork = item.get('artworkUrl100')
        cover_url = artwork.replace('100x100', '600x600') if artwork else None
        results.append({
            'source': 'itunes',
            'itunes_id': item.get('collectionId'),
            'title': item.get('collectionName', ''),
            'artist': item.get('artistName', ''),
            'label': (item.get('copyright') or '')[:200],
            'year': (item.get('releaseDate') or '')[:4] or None,
            'tracks': item.get('trackCount'),
            'genres': [item['primaryGenreName']] if item.get('primaryGenreName') else [],
            'cover_thumb': artwork,
            'cover_url': cover_url,
        })
    return results


def _search_vinyl_info_deezer(title, artist):
    query = f'{artist} {title}'.strip()
    search_url = f'https://{DEEZER_HOST}/search/album?' + urllib.parse.urlencode({
        'q': query,
        'limit': 15,
    })
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for item in data.get('data', []):
        cover_url = item.get('cover_xl') or item.get('cover_big')
        results.append({
            'source': 'deezer',
            # la ricerca Deezer non espone anno/etichetta/generi: si recuperano
            # dal dettaglio album (fetch_deezer_album) alla selezione del risultato
            'deezer_id': item.get('id'),
            'title': item.get('title', ''),
            'artist': (item.get('artist') or {}).get('name', ''),
            'label': '',
            'year': None,
            'tracks': item.get('nb_tracks'),
            'genres': [],
            'cover_thumb': item.get('cover_medium'),
            'cover_url': cover_url,
        })
    return results


def _format_duration(seconds):
    if not seconds:
        return ''
    minutes, secs = divmod(int(seconds), 60)
    return f' ({minutes}:{secs:02d})'


def fetch_deezer_album(request):
    """Recupera anno, etichetta, generi e tracklist dal dettaglio album Deezer."""
    try:
        album_id = int(request.GET.get('id', ''))
    except (TypeError, ValueError):
        return JsonResponse({})

    data = _http_get_json(f'https://{DEEZER_HOST}/album/{album_id}')
    if data is None or data.get('error'):
        return JsonResponse({})

    tracklist = '\n'.join(
        f"{t['title']}{_format_duration(t.get('duration'))}"
        for t in (data.get('tracks') or {}).get('data', [])
        if t.get('title')
    )

    return JsonResponse({
        'year': (data.get('release_date') or '')[:4] or None,
        'label': (data.get('label') or '')[:200],
        'genres': [g['name'] for g in (data.get('genres') or {}).get('data', []) if g.get('name')],
        'tracks': data.get('nb_tracks'),
        'tracklist': tracklist,
    })


def fetch_itunes_album(request):
    """Recupera la tracklist di un album tramite il lookup iTunes."""
    try:
        album_id = int(request.GET.get('id', ''))
    except (TypeError, ValueError):
        return JsonResponse({})

    lookup_url = f'https://{ITUNES_HOST}/lookup?' + urllib.parse.urlencode({
        'id': album_id,
        'entity': 'song',
        'limit': 200,
    })
    data = _http_get_json(lookup_url)
    if data is None:
        return JsonResponse({})

    songs = sorted(
        (item for item in data.get('results', []) if item.get('wrapperType') == 'track'),
        key=lambda t: (t.get('discNumber') or 1, t.get('trackNumber') or 0),
    )
    tracklist = '\n'.join(
        f"{t['trackName']}{_format_duration((t.get('trackTimeMillis') or 0) / 1000)}"
        for t in songs
        if t.get('trackName')
    )

    return JsonResponse({'tracklist': tracklist, 'tracks': len(songs) or None})


def search_vinyl_info(request):
    """Cerca metadati disco (artista, anno, tracce...) su più fonti (iTunes + Deezer)."""
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()
    if len(title) < 2:
        return JsonResponse({'results': [], 'error': 'title_too_short'})

    combined = _run_sources_parallel([
        lambda: _search_vinyl_info_itunes(title, artist),
        lambda: _search_vinyl_info_deezer(title, artist),
    ])
    if not combined:
        return JsonResponse({'results': [], 'error': 'network_error'})

    results = []
    seen = set()
    for entry in combined:
        title_key = entry['title'].strip().lower()
        artist_key = entry['artist'].strip().lower()
        if not title_key:
            continue
        dedup_key = (title_key, artist_key)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        # Rilevanza rispetto a quanto digitato: tollera refusi (es. "floid" per
        # "Floyd") meglio di un semplice confronto esatto, ed evita che un
        # risultato completamente estraneo vinca solo perché ha una copertina.
        relevance = _similarity(title, entry['title'])
        if artist:
            relevance += _similarity(artist, entry['artist'])
        entry['_relevance'] = relevance
        # Solo la copertina è un segnale di qualità confrontabile tra le fonti:
        # Deezer non restituisce l'anno nella ricerca (arriva solo dopo, alla
        # selezione), quindi penalizzarne l'assenza qui farebbe perdere sempre
        # a Deezer anche quando il suo risultato è quello giusto.
        entry['_completeness'] = 0 if entry['cover_url'] else 1
        results.append(entry)

    results.sort(key=lambda r: (-r.pop('_relevance'), r.pop('_completeness')))
    return JsonResponse({'results': results[:10]})


def search_vinyl_cover(request):
    """Cerca copertine album su più fonti in base a titolo/artista."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    combined = _run_sources_parallel([
        lambda: _search_vinyl_info_itunes(query, ''),
        lambda: _search_vinyl_info_deezer(query, ''),
    ])

    seen = set()
    results = []
    for r in combined:
        if not r['cover_url'] or not r['cover_thumb']:
            continue
        key = (r['title'].strip().lower(), r['artist'].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        results.append({
            'title': r['title'],
            'author': r['artist'],
            'year': r['year'],
            'thumb_url': r['cover_thumb'],
            'full_url': r['cover_url'],
        })

    return JsonResponse({'results': results[:16]})


def apply_vinyl_metadata(request):
    """Risolve (get-or-create) artista/etichetta/generi scelti e ne restituisce gli id per il form."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    artist = _get_or_create_artist(request.POST.get('artist', ''))
    label = _get_or_create_label(request.POST.get('label', ''))
    genres = _get_or_create_genres(request.POST.getlist('genres'))

    return JsonResponse({
        'artist': {'id': artist.id, 'label': str(artist)} if artist else None,
        'label': {'id': label.id, 'label': str(label)} if label else None,
        'genres': [{'id': g.id, 'label': g.name} for g in genres],
    })


def _download_cover(url):
    """Scarica una copertina solo dai provider consentiti (anti-SSRF)."""
    if not COVER_URL_RE.fullmatch(url):
        return None
    req = urllib.request.Request(url, headers={'User-Agent': 'PersonalLibraryApp/1.0'})
    try:
        with _OPENER.open(req, timeout=10) as resp:
            data = resp.read()
    except Exception:
        return None
    if len(data) < 500:
        return None
    return data


def _attach_cover_from_url(instance, request):
    if request.FILES.get('cover_image'):
        return
    cover_url = request.POST.get('cover_image_url')
    if not cover_url:
        return
    data = _download_cover(cover_url)
    if data:
        instance.cover_image.save(f'{instance.pk}.jpg', ContentFile(data), save=True)


def search_vinyls(request):
    query = request.GET.get('q', '')
    vinyls = Vinyl.objects.all()

    if query:
        vinyls = vinyls.filter(
            search_q(query)
        )

    context = {
        'vinyls': vinyls,
        'query': query,
        'genres': VinylGenre.objects.all(),
    }
    return render(request, 'vinyl/vinyl_list.html', context)


def statistics(request):
    total_vinyls = Vinyl.objects.count()
    available_vinyls = Vinyl.objects.filter(is_available=True).count()
    total_artists = Artist.objects.count()

    genres = VinylGenre.objects.annotate(vinyl_count=Count('vinyl'))

    context = {
        'total_vinyls': total_vinyls,
        'available_vinyls': available_vinyls,
        'total_artists': total_artists,
        'genres': genres,
    }
    return render(request, 'vinyl/statistics.html', context)


class VinylListView(ListView):
    model = Vinyl
    template_name = 'vinyl/vinyl_list.html'
    context_object_name = 'vinyls'
    paginate_by = 24

    def get_queryset(self):
        queryset = Vinyl.objects.all()

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                search_q(query)
            )

        genre_id = self.request.GET.get('genre')
        if genre_id:
            queryset = queryset.filter(genre__id=genre_id)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(is_available=status == 'true')

        sort_by = self.request.GET.get('sort', 'title')
        valid_sorts = ['title', '-title', 'artist__name', '-artist__name',
                       'release_year', '-release_year', '-rating', '-added_date']
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by, 'pk')  # 'pk' rende stabile l'ordine tra pagine

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = VinylGenre.objects.all()
        return context

    # Infinite scroll: ?partial=1 restituisce solo le copertine della pagina richiesta
    def get_template_names(self):
        if self.request.GET.get('partial'):
            return ['vinyl/_vinyl_items.html']
        return super().get_template_names()

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        page = context.get('page_obj')
        if self.request.GET.get('partial') and page and page.has_next():
            response['X-Next-Page'] = str(page.next_page_number())
        return response


class VinylDetailView(DetailView):
    model = Vinyl
    template_name = 'vinyl/vinyl_detail.html'
    context_object_name = 'vinyl'


class VinylCreateView(CreateView):
    model = Vinyl
    form_class = VinylForm
    template_name = 'vinyl/vinyl_form.html'
    success_url = reverse_lazy('vinyl:vinyl_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class VinylUpdateView(UpdateView):
    model = Vinyl
    form_class = VinylForm
    template_name = 'vinyl/vinyl_form.html'
    success_url = reverse_lazy('vinyl:vinyl_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class VinylDeleteView(DeleteView):
    model = Vinyl
    template_name = 'vinyl/vinyl_confirm_delete.html'
    success_url = reverse_lazy('vinyl:vinyl_list')


class ArtistListView(ListView):
    model = Artist
    template_name = 'vinyl/artist_list.html'
    context_object_name = 'artists'


class RecordLabelListView(ListView):
    model = RecordLabel
    template_name = 'vinyl/label_list.html'
    context_object_name = 'labels'


class GenreListView(ListView):
    model = VinylGenre
    template_name = 'vinyl/genre_list.html'
    context_object_name = 'genres'
