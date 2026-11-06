from django.views.generic import ListView

from ..models import Publisher


class PublisherListView(ListView):
    model = Publisher
    template_name = 'library/publisher_list.html'
    context_object_name = 'publishers'
