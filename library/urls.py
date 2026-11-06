from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Books
    path('', views.BookListView.as_view(), name='book_list'),
    path('search/', views.search_books, name='search_books'),
    path('<uuid:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('add/', views.BookCreateView.as_view(), name='book_add'),
    path('<uuid:pk>/edit/', views.BookUpdateView.as_view(), name='book_edit'),
    path('<uuid:pk>/delete/', views.BookDeleteView.as_view(), name='book_delete'),
    
    # Authors
    path('authors/', views.AuthorListView.as_view(), name='author_list'),
    
    # Publishers
    path('publishers/', views.PublisherListView.as_view(), name='publisher_list'),
    
    # Genres
    path('genres/', views.GenreListView.as_view(), name='genre_list'),
    
    # Statistics
    path('statistics/', views.statistics, name='statistics'),

    # Cover search (AJAX)
    path('search-cover/', views.search_cover, name='search_cover'),

    # Book metadata auto-fill (AJAX)
    path('search-book-info/', views.search_book_info, name='search_book_info'),
    path('work-description/', views.fetch_work_description, name='fetch_work_description'),
    path('apply-book-metadata/', views.apply_book_metadata, name='apply_book_metadata'),
]
