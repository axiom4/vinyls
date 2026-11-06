from django.contrib import admin
from .models import Author, Publisher, BookGenre, Book, BookRecord


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name')
    search_fields = ('first_name', 'last_name')


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)


@admin.register(BookGenre)
class BookGenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn_number', 'publication_year', 'is_available')
    list_filter = ('is_available', 'publisher', 'genre')
    search_fields = ('title', 'author__first_name', 'author__last_name', 'isbn_number')
    list_editable = ('is_available',)


@admin.register(BookRecord)
class BookRecordAdmin(admin.ModelAdmin):
    list_display = ('book', 'status', 'date_added', 'date_finished')
    list_filter = ('status', 'date_added')
    search_fields = ('book__title',)
