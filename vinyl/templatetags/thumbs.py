from pathlib import Path

from django import template
from PIL import Image

register = template.Library()


@register.filter
def thumb(field, size=400):
    """URL di una miniatura WebP (creata al primo uso accanto all'originale); in caso di errore, l'originale."""
    if not field:
        return ''
    try:
        src = Path(field.path)
        dst = src.with_name(f'{src.stem}_t{size}.webp')
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            with Image.open(src) as im:
                im.thumbnail((size, size))
                im.convert('RGB').save(dst, 'WEBP', quality=80)
        return field.url.rsplit('/', 1)[0] + '/' + dst.name
    except (OSError, ValueError):
        return field.url
