import re
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from django.http import JsonResponse

from .external import ARCHIVE_HOST, GOOGLE_BOOKS_HOST, OPEN_LIBRARY_HOST, _OPENER, _http_get_json, _run_sources_parallel


# Solo https e host esatti dei provider; il '/' dopo l'host impedisce trucchi (host.evil.com, user@host)
COVER_URL_RE = re.compile(
    r'https://(covers\.openlibrary\.org|books\.google\.com|books\.googleusercontent\.com|archive\.org)/[^\s#]*'
)


def _search_cover_openlibrary(query, limit=12):
    search_url = f'https://{OPEN_LIBRARY_HOST}/search.json?' + urllib.parse.urlencode({
        'q': query,
        'limit': limit,
        'fields': 'title,author_name,cover_i,first_publish_year',
    })
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for doc in data.get('docs', []):
        cover_id = doc.get('cover_i')
        if not cover_id:
            continue
        results.append({
            'title': doc.get('title', ''),
            'author': ', '.join(doc.get('author_name') or []),
            'year': doc.get('first_publish_year'),
            'thumb_url': f'https://covers.openlibrary.org/b/id/{cover_id}-M.jpg',
            'full_url': f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg',
        })
    return results


def _search_cover_google(query, limit=12):
    search_url = f'https://{GOOGLE_BOOKS_HOST}/books/v1/volumes?' + urllib.parse.urlencode({
        'q': query,
        'maxResults': limit,
    })
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for item in data.get('items', []):
        info = item.get('volumeInfo', {})
        image_links = info.get('imageLinks', {})
        thumb_url = image_links.get('thumbnail') or image_links.get('smallThumbnail')
        full_url = image_links.get('large') or image_links.get('medium') or thumb_url
        if not thumb_url or not full_url:
            continue
        results.append({
            'title': info.get('title', ''),
            'author': ', '.join(info.get('authors') or []),
            'year': (info.get('publishedDate') or '')[:4] or None,
            'thumb_url': thumb_url.replace('http://', 'https://'),
            'full_url': full_url.replace('http://', 'https://'),
        })
    return results


def _search_cover_archive(query, limit=12):
    params = [
        ('q', f'{query} AND mediatype:texts'),
        ('fl[]', 'identifier'),
        ('fl[]', 'title'),
        ('fl[]', 'creator'),
        ('fl[]', 'year'),
        ('rows', limit),
        ('output', 'json'),
    ]
    search_url = f'https://{ARCHIVE_HOST}/advancedsearch.php?' + urllib.parse.urlencode(params)
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for doc in data.get('response', {}).get('docs', []):
        identifier = doc.get('identifier')
        if not identifier:
            continue
        creator = doc.get('creator', '')
        if isinstance(creator, list):
            creator = ', '.join(creator)
        cover_url = f'https://{ARCHIVE_HOST}/services/img/{identifier}'
        results.append({
            'title': doc.get('title', ''),
            'author': creator,
            'year': str(doc.get('year')) if doc.get('year') else None,
            'thumb_url': cover_url,
            'full_url': cover_url,
        })
    return results


def search_cover(request):
    """Cerca copertine su più fonti (Open Library + Google Books + Internet Archive) in base a titolo/autore."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    results = _run_sources_parallel([
        lambda: _search_cover_openlibrary(query),
        lambda: _search_cover_google(query),
        lambda: _search_cover_archive(query),
    ])

    seen = set()
    deduped = []
    for r in results:
        key = (r['title'].strip().lower(), r['author'].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return JsonResponse({'results': deduped[:16]})


def _download_cover(url):
    """Scarica una copertina solo dai provider di copertine consentiti (anti-SSRF)."""
    if not COVER_URL_RE.fullmatch(url):
        return None
    req = urllib.request.Request(url, headers={'User-Agent': 'PersonalLibraryApp/1.0'})
    try:
        with _OPENER.open(req, timeout=10) as resp:
            data = resp.read()
    except Exception:
        return None
    # Open Library restituisce una piccola immagine placeholder se non trova la copertina
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
