from django.shortcuts import render

from .forms import CitySearchForm
from .models import WeatherData
from .services import (
    get_weather_data,
    parse_weather_data,
    get_forecast_data,
    parse_forecast_data,
    summarize_daily_forecast,
    calculate_forecast_statistics,
)


def home(request):
    statistics = None
    form = CitySearchForm()
    weather = None
    error = None
    forecast = None
    forecast_chart = None
    humidity_chart = None
    forecast_error = None

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
                forecast_data = get_forecast_data(city)

                if "error" in forecast_data:
                    forecast_error = forecast_data["error"]
                else:
                    parsed_forecast = parse_forecast_data(forecast_data)

                    statistics = calculate_forecast_statistics(parsed_forecast)

                    forecast = {
                        "city": parsed_forecast["city"],
                        "country": parsed_forecast["country"],
                        "forecast": summarize_daily_forecast(parsed_forecast),
                    }
                    forecast_chart = {
                        "labels": [entry["datetime"] for entry in parsed_forecast["forecast"]],
                        "temperatures": [entry["temperature"] for entry in parsed_forecast["forecast"]],
                    }
                    humidity_chart = {
                        "labels": [entry["datetime"] for entry in parsed_forecast["forecast"]],
                        "humidities": [entry["humidity"] for entry in parsed_forecast["forecast"]],
                    }



    history = WeatherData.objects.all()

    latest_searches = history[:10]

    city_weather = None

    searched_city = request.GET.get("city")

    if searched_city:
        city_weather = WeatherData.objects.filter(
            city__iexact=searched_city
        )

    return render(
        request,
        "weather/home.html",
        {
            "form": form,
            "weather": weather,
            "error": error,
            "history": history,
            "latest_searches": latest_searches,
            "city_weather": city_weather,
            "forecast": forecast,
            "forecast_chart": forecast_chart,
            "humidity_chart": humidity_chart,
            "forecast_error": forecast_error,
            "statistics": statistics,
        },
    )