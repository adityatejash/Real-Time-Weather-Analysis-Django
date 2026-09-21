from django.shortcuts import render

from .forms import CitySearchForm
from .services import get_weather_data, parse_weather_data


def home(request):
    form = CitySearchForm()
    weather = None

    if request.method == "GET" and request.GET.get("city"):
        form = CitySearchForm(request.GET)

        if form.is_valid():
            city = form.cleaned_data["city"]

            data = get_weather_data(city)
            weather = parse_weather_data(data)

    return render(
        request,
        "weather/home.html",
        {
            "form": form,
            "weather": weather,
        },
    )