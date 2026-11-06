from django.conf import settings


def css_version(request):
    """Versione = mtime di style.css: i browser (Safari su iPhone/iPad) ricaricano il CSS quando cambia."""
    try:
        return {'CSS_VERSION': int((settings.BASE_DIR / 'static/css/style.css').stat().st_mtime)}
    except OSError:
        return {'CSS_VERSION': 0}
