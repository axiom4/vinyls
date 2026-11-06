from django.db.models import Count
from django.shortcuts import render

from ..models import Book, BookGenre, BookRecord


def statistics(request):
    total_books = Book.objects.count()
    available_books = Book.objects.filter(is_available=True).count()
    read_books = BookRecord.objects.filter(status='read').count()
    
    # Books by genre
    genres = BookGenre.objects.annotate(book_count=Count('book'))
    
    context = {
        'total_books': total_books,
        'available_books': available_books,
        'read_books': read_books,
        'genres': genres,
    }
    return render(request, 'library/statistics.html', context)
