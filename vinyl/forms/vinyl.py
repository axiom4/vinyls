from django import forms

from ..models import Vinyl


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
