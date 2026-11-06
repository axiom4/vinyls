import urllib.parse
import urllib.request

from django.http import JsonResponse

from ..models import Artist, RecordLabel, VinylGenre
from .external import _http_get_json, _run_sources_parallel, _similarity


ITUNES_HOST = 'itunes.apple.com'
DEEZER_HOST = 'api.deezer.com'


MAX_DESCRIPTION_LENGTH = 500


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
