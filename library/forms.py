from django import forms
from .models import Book, BookGenre, Author, Publisher


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'publisher', 'isbn_type', 'isbn_number',
                  'genre', 'publication_year', 'pages', 'language',
                  'description', 'cover_image', 'rating', 'is_available']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.Select(attrs={'class': 'form-select'}),
            'publisher': forms.Select(attrs={'class': 'form-select'}),
            'isbn_type': forms.Select(attrs={'class': 'form-select'}),
            'isbn_number': forms.TextInput(attrs={'class': 'form-control'}),
            'genre': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control'}),
            'language': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '5'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PublisherForm(forms.ModelForm):
    class Meta:
        model = Publisher
        fields = ['name', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class BookGenreForm(forms.ModelForm):
    class Meta:
        model = BookGenre
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
