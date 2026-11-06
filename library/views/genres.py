from django.views.generic import ListView

from ..models import BookGenre


class GenreListView(ListView):
    model = BookGenre
    template_name = 'library/genre_list.html'
    context_object_name = 'genres'
