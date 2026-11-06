from django.views.generic import ListView

from ..models import RecordLabel


class RecordLabelListView(ListView):
    model = RecordLabel
    template_name = 'vinyl/label_list.html'
    context_object_name = 'labels'
