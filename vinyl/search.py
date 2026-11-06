import unicodedata

from django.db.backends.signals import connection_created
from django.db.models import CharField, Q, Transform


def fold(text):
    """Minuscolo e senza accenti/diacritici: 'Måneskin' -> 'maneskin'."""
    decomposed = unicodedata.normalize('NFKD', str(text).casefold())
    return ''.join(c for c in decomposed if not unicodedata.combining(c))


@CharField.register_lookup
class Fold(Transform):
    lookup_name = 'fold'
    function = 'FOLD'


def _register_sqlite_fold(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        connection.connection.create_function('FOLD', 1, lambda v: None if v is None else fold(v), deterministic=True)


connection_created.connect(_register_sqlite_fold)


def search_q(query):
    """Q accent/case-insensitive su titolo, artista e numero di catalogo."""
    q = fold(query)
    return (Q(title__fold__contains=q) | Q(artist__name__fold__contains=q)
            | Q(catalog_number__fold__contains=q))
