import difflib
import hashlib
import itertools
import json
import logging
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.cache import cache


OPEN_LIBRARY_HOST = 'openlibrary.org'
GOOGLE_BOOKS_HOST = 'www.googleapis.com'


ARCHIVE_HOST = 'archive.org'


logger = logging.getLogger(__name__)


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
        logger.warning('cache non disponibile, risposta non salvata', exc_info=True)
    return data


def _run_sources_parallel(tasks, timeout=8):
    """Interroga le fonti in parallelo; chi non risponde entro il timeout viene ignorato.

    I risultati vengono alternati (round-robin) tra le fonti anziché concatenati:
    altrimenti, se una fonte restituisce molti candidati "completi" (con copertina/ISBN),
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
