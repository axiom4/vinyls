import re
import urllib.parse
import urllib.request

from django.http import JsonResponse

from ..models import Author, BookGenre, Publisher
from .external import ARCHIVE_HOST, GOOGLE_BOOKS_HOST, OPEN_LIBRARY_HOST, _http_get_json, _run_sources_parallel, _similarity


MAX_DESCRIPTION_LENGTH = 500
LANGUAGE_LABELS = {
    'ita': 'Italiano',
    'eng': 'Inglese',
    'fre': 'Francese',
    'fra': 'Francese',
    'ger': 'Tedesco',
    'deu': 'Tedesco',
    'spa': 'Spagnolo',
    'por': 'Portoghese',
}


# Codice lingua ISO 639-1 usato da Google Books, a partire dal codice a 3 lettere di Open Library
GOOGLE_LANG_CODES = {
    'ita': 'it',
    'eng': 'en',
    'fre': 'fr',
    'ger': 'de',
    'spa': 'es',
    'por': 'pt',
}


def _normalize_person_name(full_name):
    """Riporta a un formato uniforme 'Nome Cognome' i nomi che arrivano da fonti diverse.

    Internet Archive/cataloghi bibliotecari restituiscono spesso 'Cognome, Nome, 1964-'
    mentre Open Library/Google Books usano 'Nome Cognome': senza normalizzare, la
    stessa persona finisce per generare un Author diverso ad ogni fonte.
    """
    name = full_name.strip()
    # rimuove annotazioni di nascita/morte in stile catalogo, es. ", 1964-" o ", 1911-1980."
    name = re.sub(r',?\s*\d{3,4}-\d{0,4}\.?$', '', name).strip()
    if ',' in name:
        last, _, rest = name.partition(',')
        rest = rest.strip(' ,')
        name = f'{rest} {last.strip()}'.strip() if rest else last.strip()
    return re.sub(r'\s+', ' ', name).strip()


def _get_or_create_author(full_name):
    name = _normalize_person_name(full_name)
    if not name:
        return None
    parts = name.split()
    if len(parts) == 1:
        first_name, last_name = '', parts[0]
    else:
        first_name, last_name = ' '.join(parts[:-1]), parts[-1]

    existing = Author.objects.filter(first_name__iexact=first_name, last_name__iexact=last_name).first()
    if existing:
        return existing
    return Author.objects.create(first_name=first_name, last_name=last_name)


def _get_or_create_publisher(name):
    name = name.strip()
    if not name:
        return None
    publisher, _ = Publisher.objects.get_or_create(name=name[:200])
    return publisher


def _get_or_create_genres(names):
    genres = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        genre, _ = BookGenre.objects.get_or_create(name=name[:100])
        genres.append(genre)
    return genres


def _search_book_info_openlibrary(title, author, language_code):
    query = f'title:"{title}"'
    if author:
        query += f' author:"{author}"'
    if language_code in LANGUAGE_LABELS:
        query += f' language:{language_code}'

    search_url = f'https://{OPEN_LIBRARY_HOST}/search.json?' + urllib.parse.urlencode({
        'q': query,
        'limit': 20,
        'fields': 'key,title,author_name,first_publish_year,publisher,isbn,'
                  'number_of_pages_median,language,subject,cover_i,edition_count,'
                  'ratings_average',
    })
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for doc in data.get('docs', []):
        isbn_list = doc.get('isbn') or []
        isbn13 = next((i for i in isbn_list if len(i) == 13), None)
        isbn10 = next((i for i in isbn_list if len(i) == 10), None)
        lang_code = (doc.get('language') or [None])[0]
        cover_id = doc.get('cover_i')
        results.append({
            'source': 'openlibrary',
            'title': doc.get('title', ''),
            'author': ', '.join(doc.get('author_name') or []),
            'publisher': (doc.get('publisher') or [''])[0],
            'year': doc.get('first_publish_year'),
            'pages': doc.get('number_of_pages_median'),
            'language': LANGUAGE_LABELS.get(lang_code, ''),
            'isbn13': isbn13,
            'isbn10': isbn10,
            'genres': (doc.get('subject') or [])[:3],
            'work_key': doc.get('key'),
            'description': None,
            'rating': round(doc['ratings_average'], 1) if doc.get('ratings_average') else None,
            'cover_url': f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg' if cover_id else None,
        })
    return results


def _search_book_info_google(title, author, language_code):
    query = f'intitle:{title}'
    if author:
        query += f'+inauthor:{author}'

    params = {'q': query, 'maxResults': 20}
    lang_restrict = GOOGLE_LANG_CODES.get(language_code)
    if lang_restrict:
        params['langRestrict'] = lang_restrict

    search_url = f'https://{GOOGLE_BOOKS_HOST}/books/v1/volumes?' + urllib.parse.urlencode(params)
    data = _http_get_json(search_url)
    if data is None:
        return []

    results = []
    for item in data.get('items', []):
        info = item.get('volumeInfo', {})
        identifiers = info.get('industryIdentifiers', [])
        isbn13 = next((i['identifier'] for i in identifiers if i.get('type') == 'ISBN_13'), None)
        isbn10 = next((i['identifier'] for i in identifiers if i.get('type') == 'ISBN_10'), None)
        image_links = info.get('imageLinks', {})
        cover_url = image_links.get('large') or image_links.get('thumbnail') or image_links.get('smallThumbnail')
        if cover_url:
            cover_url = cover_url.replace('http://', 'https://')
        description = (info.get('description') or '').strip()
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH].rsplit(' ', 1)[0] + '…'
        lang_code_2 = info.get('language', '')
        language_label = next(
            (LANGUAGE_LABELS[k] for k, v in GOOGLE_LANG_CODES.items() if v == lang_code_2 and k in LANGUAGE_LABELS),
            ''
        )
        results.append({
            'source': 'googlebooks',
            'title': info.get('title', ''),
            'author': ', '.join(info.get('authors') or []),
            'publisher': info.get('publisher', ''),
            'year': (info.get('publishedDate') or '')[:4] or None,
            'pages': info.get('pageCount'),
            'language': language_label,
            'isbn13': isbn13,
            'isbn10': isbn10,
            'genres': (info.get('categories') or [])[:3],
            'work_key': None,
            'description': description or None,
            'rating': round(float(info['averageRating']), 1) if info.get('averageRating') else None,
            'cover_url': cover_url,
        })
    return results


def _search_book_info_archive(title, author, language_code):
    query = f'title:"{title}"'
    if author:
        query += f' AND creator:"{author}"'
    query += ' AND mediatype:texts'

    params = [
        ('q', query),
        ('fl[]', 'identifier'),
        ('fl[]', 'title'),
        ('fl[]', 'creator'),
        ('fl[]', 'year'),
        ('fl[]', 'publisher'),
        ('fl[]', 'language'),
        ('fl[]', 'isbn'),
        ('rows', 15),
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
        isbn_list = doc.get('isbn') or []
        if isinstance(isbn_list, str):
            isbn_list = [isbn_list]
        isbn13 = next((i for i in isbn_list if len(i) == 13), None)
        isbn10 = next((i for i in isbn_list if len(i) == 10), None)
        language = doc.get('language', '')
        if isinstance(language, list):
            language = language[0] if language else ''
        results.append({
            'source': 'archive',
            'archive_id': identifier,
            'title': doc.get('title', ''),
            'author': creator,
            'publisher': doc.get('publisher', '') if isinstance(doc.get('publisher'), str) else '',
            'year': str(doc.get('year')) if doc.get('year') else None,
            'pages': None,
            'language': language,
            'isbn13': isbn13,
            'isbn10': isbn10,
            'genres': [],
            'work_key': None,
            'description': None,
            'rating': None,
            'cover_url': f'https://{ARCHIVE_HOST}/services/img/{identifier}',
        })
    return results


def search_book_info(request):
    """Cerca metadati libro (autore, editore, isbn, anno...) su più fonti (Open Library + Google Books)."""
    title = request.GET.get('title', '').strip()
    author = request.GET.get('author', '').strip()
    if len(title) < 2:
        return JsonResponse({'results': [], 'error': 'title_too_short'})

    language_code = request.GET.get('language', '').strip().lower()

    combined = _run_sources_parallel([
        lambda: _search_book_info_openlibrary(title, author, language_code),
        lambda: _search_book_info_google(title, author, language_code),
        lambda: _search_book_info_archive(title, author, language_code),
    ])
    if not combined:
        return JsonResponse({'results': [], 'error': 'network_error'})

    results = []
    seen = set()
    for entry in combined:
        title_key = entry['title'].strip().lower()
        author_key = entry['author'].strip().lower()
        if not title_key:
            continue
        dedup_key = (title_key, author_key)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        # Rilevanza rispetto a quanto digitato: tollera refusi e ordina prima
        # i risultati vicini alla ricerca, invece di lasciare che un titolo
        # estraneo vinca solo perché ha copertina/ISBN disponibili.
        relevance = _similarity(title, entry['title'])
        if author:
            relevance += _similarity(author, entry['author'])
        entry['_relevance'] = relevance
        entry['_completeness'] = (
            (0 if entry['cover_url'] else 1)
            + (0 if (entry['isbn13'] or entry['isbn10']) else 1)
        )
        results.append(entry)

    results.sort(key=lambda r: (-r.pop('_relevance'), r.pop('_completeness')))
    return JsonResponse({'results': results[:10]})


def fetch_work_description(request):
    """Recupera una breve sinossi dell'opera da Open Library (troncata)."""
    key = request.GET.get('key', '')
    if not re.fullmatch(r'/works/OL\d+W', key):
        return JsonResponse({'description': ''})

    url = f'https://{OPEN_LIBRARY_HOST}{key}.json'
    data = _http_get_json(url)
    if data is None:
        return JsonResponse({'description': ''})

    description = data.get('description', '')
    if isinstance(description, dict):
        description = description.get('value', '')
    description = (description or '').strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        description = description[:MAX_DESCRIPTION_LENGTH].rsplit(' ', 1)[0] + '…'
    return JsonResponse({'description': description})


def apply_book_metadata(request):
    """Risolve (get-or-create) autore/editore/generi scelti e ne restituisce gli id per il form."""
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    author = _get_or_create_author(request.POST.get('author', ''))
    publisher = _get_or_create_publisher(request.POST.get('publisher', ''))
    genres = _get_or_create_genres(request.POST.getlist('genres'))

    return JsonResponse({
        'author': {'id': author.id, 'label': str(author)} if author else None,
        'publisher': {'id': publisher.id, 'label': str(publisher)} if publisher else None,
        'genres': [{'id': g.id, 'label': g.name} for g in genres],
    })
