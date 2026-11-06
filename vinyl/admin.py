from django.contrib import admin
from .models import Artist, RecordLabel, VinylGenre, Vinyl


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(RecordLabel)
class RecordLabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)


@admin.register(VinylGenre)
class VinylGenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Vinyl)
class VinylAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'release_year', 'size', 'speed', 'condition', 'is_available')
    list_filter = ('is_available', 'size', 'speed', 'condition', 'label', 'genre')
    search_fields = ('title', 'artist__name', 'catalog_number')
    list_editable = ('is_available',)
