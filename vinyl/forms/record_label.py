from django import forms

from ..models import RecordLabel


class RecordLabelForm(forms.ModelForm):
    class Meta:
        model = RecordLabel
        fields = ['name', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
