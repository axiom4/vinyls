from django import forms

from ..models import VinylGenre


class VinylGenreForm(forms.ModelForm):
    class Meta:
        model = VinylGenre
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
