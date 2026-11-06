from django.conf import settings

_ASSETS = ('static/css/style.css', 'static/js/vinyl-list.js', 'static/js/lang.js')


def css_version(request):
    """Versione = mtime più recente di CSS/JS propri: i browser (Safari su iPhone/iPad) li ricaricano quando cambiano."""
    try:
        return {'CSS_VERSION': int(max((settings.BASE_DIR / p).stat().st_mtime for p in _ASSETS))}
    except OSError:
        return {'CSS_VERSION': 0}
