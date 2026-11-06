from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import BookForm
from ..models import Book, BookGenre
from .covers import _attach_cover_from_url


def search_books(request):
    query = request.GET.get('q', '')
    books = Book.objects.all()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query) |
            Q(isbn_number__icontains=query)
        )

    context = {
        'books': books,
        'query': query,
        'genres': BookGenre.objects.all(),
    }
    return render(request, 'library/book_list.html', context)


# Class-based views for books
class BookListView(ListView):
    model = Book
    template_name = 'library/book_list.html'
    context_object_name = 'books'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Book.objects.all()

        # Filter by search query
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(author__first_name__icontains=query) |
                Q(author__last_name__icontains=query) |
                Q(isbn_number__icontains=query)
            )

        # Filter by genre
        genre_id = self.request.GET.get('genre')
        if genre_id:
            queryset = queryset.filter(genre__id=genre_id)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(is_available=status == 'true')
        
        # Sort
        sort_by = self.request.GET.get('sort', '-added_date')
        valid_sorts = ['title', '-title', 'author__last_name', 
                       '-author__last_name', 'publication_year', 
                       '-publication_year', '-rating']
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['genres'] = BookGenre.objects.all()
        return context


class BookDetailView(DetailView):
    model = Book
    template_name = 'library/book_detail.html'
    context_object_name = 'book'


class BookCreateView(CreateView):
    model = Book
    form_class = BookForm
    template_name = 'library/book_form.html'
    success_url = reverse_lazy('library:book_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class BookUpdateView(UpdateView):
    model = Book
    form_class = BookForm
    template_name = 'library/book_form.html'
    success_url = reverse_lazy('library:book_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        _attach_cover_from_url(self.object, self.request)
        return response


class BookDeleteView(DeleteView):
    model = Book
    template_name = 'library/book_confirm_delete.html'
    success_url = reverse_lazy('library:book_list')
