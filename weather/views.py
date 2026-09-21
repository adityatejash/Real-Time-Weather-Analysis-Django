from django.shortcuts import render

from .forms import CitySearchForm
from .models import WeatherData
from .services import get_weather_data, parse_weather_data


def home(request):
    form = CitySearchForm()
    weather = None
    error = None

    if request.method == "GET" and request.GET.get("city"):
        form = CitySearchForm(request.GET)

        if form.is_valid():
            city = form.cleaned_data["city"]

            data = get_weather_data(city)

            if "error" in data:
                error = data["error"]
            else:
                weather = parse_weather_data(data)

                WeatherData.objects.create(
                    city=weather["city"],
                    country=weather["country"],
                    temperature=weather["temperature"],
                    feels_like=weather["feels_like"],
                    humidity=weather["humidity"],
                    pressure=weather["pressure"],
                    description=weather["description"],
                    wind_speed=weather["wind_speed"],
                    clouds=weather["clouds"],
                )

    history = WeatherData.objects.order_by("-searched_at")

    return render(
        request,
        "weather/home.html",
        {
            "form": form,
            "weather": weather,
            "error": error,
            "history": history,
        },
    )