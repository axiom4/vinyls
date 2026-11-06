from django import forms

from ..models import Publisher


class PublisherForm(forms.ModelForm):
    class Meta:
        model = Publisher
        fields = ['name', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
