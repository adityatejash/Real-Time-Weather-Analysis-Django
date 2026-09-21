from django import forms


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