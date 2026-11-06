import re
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile

from .external import _OPENER


# Solo https, host = sottodomini alfanumerici di mzstatic.com / dzcdn.net, niente userinfo/porta
COVER_URL_RE = re.compile(r'https://[a-z0-9-]+(\.[a-z0-9-]+)*\.(mzstatic\.com|dzcdn\.net)/[^\s#]*')


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
