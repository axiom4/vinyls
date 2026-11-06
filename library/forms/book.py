from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'publisher', 'isbn_type', 'isbn_number',
                  'genre', 'publication_year', 'pages', 'language',
                  'description', 'cover_image', 'rating', 'is_available']
        labels = {
            'title': _('Titolo'),
            'author': _('Autore'),
            'publisher': _('Editore'),
            'isbn_type': _('Tipo di ISBN'),
            'isbn_number': _('Numero ISBN'),
            'genre': _('Generi'),
            'publication_year': _('Anno di pubblicazione'),
            'pages': _('Pagine'),
            'language': _('Lingua'),
            'description': _('Descrizione'),
            'cover_image': _('Copertina'),
            'rating': _('Valutazione'),
            'is_available': _('Disponibile'),
        }
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
