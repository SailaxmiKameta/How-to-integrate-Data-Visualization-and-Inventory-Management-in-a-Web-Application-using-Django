from django.contrib.auth.forms import AuthenticationForm
from django import forms
from .models import Sales


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class SalesForm(forms.ModelForm):
    class Meta:
        model = Sales
        fields = ['store', 'date', 'sales', 'customers', 'open', 'promo', 'state_holiday', 'school_holiday']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'sales': forms.NumberInput(attrs={'step': '0.01'}),
        }
