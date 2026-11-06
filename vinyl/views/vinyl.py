from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import VinylForm
from ..models import Vinyl, VinylGenre
from ..search import search_q
from .covers import _attach_cover_from_url


class VinylListView(ListView):
    model = Vinyl
    template_name = 'vinyl/vinyl_list.html'
    context_object_name = 'vinyls'
    paginate_by = 24

    def get_queryset(self):
        queryset = Vinyl.objects.all()

        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                search_q(query)
            )

        genre_id = self.request.GET.get('genre')
        if genre_id:
            queryset = queryset.filter(genre__id=genre_id)

        sort_by = self.request.GET.get('sort', 'title')
        valid_sorts = ['title', '-title', 'artist__name', '-artist__name',
                       'release_year', '-release_year', '-rating', '-added_date']
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by, 'pk')  # 'pk' rende stabile l'ordine tra pagine

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = VinylGenre.objects.all()
        context['query'] = self.request.GET.get('q', '').strip()
        genre_id = self.request.GET.get('genre')
        if genre_id:
            context['active_genre'] = context['genres'].filter(pk=genre_id).first()
        return context

    # Infinite scroll: ?partial=1 restituisce solo le copertine della pagina richiesta
    def get_template_names(self):
        if self.request.GET.get('partial'):
            return ['vinyl/_vinyl_items.html']
        return super().get_template_names()

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        page = context.get('page_obj')
        if self.request.GET.get('partial') and page and page.has_next():
            response['X-Next-Page'] = str(page.next_page_number())
        return response


class VinylDetailView(DetailView):
    model = Vinyl
    template_name = 'vinyl/vinyl_detail.html'
    context_object_name = 'vinyl'


class VinylCreateView(CreateView):
    model = Vinyl
    form_class = VinylForm
    template_name = 'vinyl/vinyl_form.html'
    success_url = reverse_lazy('vinyl:vinyl_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class VinylUpdateView(UpdateView):
    model = Vinyl
    form_class = VinylForm
    template_name = 'vinyl/vinyl_form.html'
    success_url = reverse_lazy('vinyl:vinyl_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class VinylDeleteView(DeleteView):
    model = Vinyl
    template_name = 'vinyl/vinyl_confirm_delete.html'
    success_url = reverse_lazy('vinyl:vinyl_list')
