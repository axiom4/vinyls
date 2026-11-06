from django.views.generic import ListView

from ..models import VinylGenre


class GenreListView(ListView):
    model = VinylGenre
    template_name = 'vinyl/genre_list.html'
    context_object_name = 'genres'
