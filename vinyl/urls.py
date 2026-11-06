from django.urls import path
from . import views

app_name = 'vinyl'

urlpatterns = [
    # Vinyls
    path('', views.VinylListView.as_view(), name='vinyl_list'),
    path('search/', views.search_vinyls, name='search_vinyls'),
    path('<uuid:pk>/', views.VinylDetailView.as_view(), name='vinyl_detail'),
    path('add/', views.VinylCreateView.as_view(), name='vinyl_add'),
    path('<uuid:pk>/edit/', views.VinylUpdateView.as_view(), name='vinyl_edit'),
    path('<uuid:pk>/delete/', views.VinylDeleteView.as_view(), name='vinyl_delete'),

    # Artists
    path('artists/', views.ArtistListView.as_view(), name='artist_list'),

    # Labels
    path('labels/', views.RecordLabelListView.as_view(), name='label_list'),

    # Genres
    path('genres/', views.GenreListView.as_view(), name='genre_list'),

    # Statistics
    path('statistics/', views.statistics, name='statistics'),

    # Online search (AJAX)
    path('search-cover/', views.search_vinyl_cover, name='search_cover'),
    path('search-vinyl-info/', views.search_vinyl_info, name='search_vinyl_info'),
    path('deezer-album/', views.fetch_deezer_album, name='fetch_deezer_album'),
    path('itunes-album/', views.fetch_itunes_album, name='fetch_itunes_album'),
    path('apply-vinyl-metadata/', views.apply_vinyl_metadata, name='apply_vinyl_metadata'),
]
