from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CitySearchForm(forms.Form):
    city = forms.CharField(
        max_length=100,
        required=True,
        label="City",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter city name",
            }
        ),
    )


class RegistrationForm(UserCreationForm):
    """Registration form extending UserCreationForm with an email field."""

    email = forms.EmailField(required=True, label="Email address")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "password1": forms.PasswordInput(attrs={"autocomplete": "new-password"}),
            "password2": forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        }