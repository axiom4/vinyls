from django import forms
from .models import Vinyl, Artist, RecordLabel, VinylGenre


class VinylForm(forms.ModelForm):
    class Meta:
        model = Vinyl
        fields = ['title', 'artist', 'label', 'genre', 'release_year', 'size',
                  'speed', 'condition', 'catalog_number', 'tracks', 'tracklist',
                  'description', 'cover_image', 'rating', 'is_available']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'artist': forms.Select(attrs={'class': 'form-select'}),
            'label': forms.Select(attrs={'class': 'form-select'}),
            'genre': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'release_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-select'}),
            'speed': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'catalog_number': forms.TextInput(attrs={'class': 'form-control'}),
            'tracks': forms.NumberInput(attrs={'class': 'form-control'}),
            'tracklist': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '5'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ArtistForm(forms.ModelForm):
    class Meta:
        model = Artist
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class RecordLabelForm(forms.ModelForm):
    class Meta:
        model = RecordLabel
        fields = ['name', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class VinylGenreForm(forms.ModelForm):
    class Meta:
        model = VinylGenre
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
