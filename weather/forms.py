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
    email = forms.EmailField(
        required=True,
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email address",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists."
            )

        return email