from datetime import date

from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import CitySearchForm, RegistrationForm
from .models import WeatherData
from .services import (
    get_weather_data,
    parse_weather_data,
    get_forecast_data,
    parse_forecast_data,
    summarize_daily_forecast,
    calculate_forecast_statistics,
    generate_weather_insights,
    analyze_weather_history,
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
    insights = None

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
                    insights = generate_weather_insights(weather, {})
                else:
                    parsed_forecast = parse_forecast_data(forecast_data)

                    statistics = calculate_forecast_statistics(parsed_forecast)
                    insights = generate_weather_insights(weather, parsed_forecast)

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
            "insights": insights,
        },
    )


def history_view(request):
    """Render the historical weather analysis page with optional filters.

    Reads city, start_date, and end_date from GET parameters, validates them,
    and delegates to analyze_weather_history(). Validation errors are shown
    without calling the service so invalid filters never produce misleading
    results.
    """
    city = request.GET.get("city", "").strip()
    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()

    start_date = None
    end_date = None
    validation_error = None

    if start_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            validation_error = "Invalid start date. Please use YYYY-MM-DD format."

    if end_date_str and not validation_error:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            validation_error = "Invalid end date. Please use YYYY-MM-DD format."

    if not validation_error and start_date and end_date and start_date > end_date:
        validation_error = "Start date cannot be later than end date."

    result = None
    if not validation_error:
        result = analyze_weather_history(city or None, start_date, end_date)

    return render(
        request,
        "weather/history.html",
        {
            "city": city,
            "start_date": start_date_str,
            "end_date": end_date_str,
            "result": result,
            "validation_error": validation_error,
        },
    )


def register(request):
    """Handle user registration.

    Authenticated users are redirected to the home page. On a valid POST,
    creates a new user (without logging them in) and redirects to the home
    page with a success message. Invalid submissions re-render the form with
    field-level errors.
    """
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Registration successful. Your account has been created.",
            )
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(request, "weather/register.html", {"form": form})