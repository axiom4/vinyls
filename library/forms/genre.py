from django import forms

from ..models import BookGenre


class BookGenreForm(forms.ModelForm):
    class Meta:
        model = BookGenre
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }
