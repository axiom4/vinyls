from django.views.generic import ListView

from ..models import Artist


class ArtistListView(ListView):
    model = Artist
    template_name = 'vinyl/artist_list.html'
    context_object_name = 'artists'
