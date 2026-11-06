from django.views.generic import ListView

from ..models import Author


# Views for authors, publishers, genres
class AuthorListView(ListView):
    model = Author
    template_name = 'library/author_list.html'
    context_object_name = 'authors'
