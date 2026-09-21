from django.shortcuts import render

from .forms import CitySearchForm


def home(request):
    form = CitySearchForm()

    return render(
        request,
        "weather/home.html",
        {"form": form},
    )