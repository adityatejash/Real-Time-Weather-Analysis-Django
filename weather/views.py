from datetime import date

from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CitySearchForm, RegistrationForm
from .models import WeatherData, FavoriteCity, City

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
                    user=request.user if request.user.is_authenticated else None,
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

                    statistics = calculate_forecast_statistics(
                        parsed_forecast
                    )
                    insights = generate_weather_insights(
                        weather, parsed_forecast
                    )

                    forecast = {
                        "city": parsed_forecast["city"],
                        "country": parsed_forecast["country"],
                        "forecast": summarize_daily_forecast(
                            parsed_forecast
                        ),
                    }
                    forecast_chart = {
                        "labels": [
                            entry["datetime"]
                            for entry in parsed_forecast["forecast"]
                        ],
                        "temperatures": [
                            entry["temperature"]
                            for entry in parsed_forecast["forecast"]
                        ],
                    }
                    humidity_chart = {
                        "labels": [
                            entry["datetime"]
                            for entry in parsed_forecast["forecast"]
                        ],
                        "humidities": [
                            entry["humidity"]
                            for entry in parsed_forecast["forecast"]
                        ],
                    }


    if request.user.is_authenticated:
        history = WeatherData.objects.filter(user=request.user)
        favorites = FavoriteCity.objects.filter(
            user=request.user
        ).order_by("city")
    else:
        history = WeatherData.objects.none()
        favorites = FavoriteCity.objects.none()


    latest_searches = history[:10]
    city_weather = None
    searched_city = request.GET.get("city")

    if searched_city and request.user.is_authenticated:
        city_weather = history.filter(
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
            "favorites": favorites,
        },
    )


def city_autocomplete(request):
    """JSON endpoint returning city suggestions for the autocomplete dropdown.

    Backed by the locally imported GeoNames City dataset (API-free, no external
    API key required). Query params:
      q      - search prefix (required, 2..100 characters)
      limit  - max results (default 10, maximum 50)
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    query = (request.GET.get("q") or "").strip()
    if not query:
        return JsonResponse(
            {"error": "Query parameter 'q' is required."}, status=400
        )
    if len(query) < 2:
        return JsonResponse(
            {"error": "Enter at least 2 characters to search cities."}, status=400
        )
    if len(query) > 100:
        return JsonResponse(
            {"error": "City search query is too long (max 100 characters)."},
            status=400,
        )

    try:
        limit = int(request.GET.get("limit", 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 50))

    suggestions = (
        City.objects.filter(name__istartswith=query)
        .order_by("-population", "name")[:limit]
        .values("name", "region", "country", "latitude", "longitude")
    )

    results = [
        {
            "name": item["name"],
            "region": item["region"],
            "country": item["country"],
            "display_name": ", ".join(
                [item["name"]]
                + ([item["region"]] if item["region"] else [])
                + [item["country"]]
            ),
            "latitude": item["latitude"],
            "longitude": item["longitude"],
        }
        for item in suggestions
    ]

    return JsonResponse({"results": results, "count": len(results)})


@login_required(login_url="login")
def history_view(request):
    """Render historical weather analysis with optional filters."""
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
            validation_error = (
                "Invalid start date. Please use YYYY-MM-DD format."
            )

    if end_date_str and not validation_error:
        try:
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            validation_error = (
                "Invalid end date. Please use YYYY-MM-DD format."
            )

    if (
        not validation_error
        and start_date
        and end_date
        and start_date > end_date
    ):
        validation_error = "Start date cannot be later than end date."

    result = None
    if not validation_error:
        result = analyze_weather_history(
            city or None,
            start_date,
            end_date,
            user=request.user,
        )

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
    """Register a new user and log them in."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Your account has been created successfully!",
            )
            return redirect("home")
    else:
        form = RegistrationForm()

    return render(
        request,
        "weather/register.html",
        {"form": form},
    )

def login_view(request):
    """Authenticate a user and start their session."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                "You have logged in successfully!",
            )

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("home")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "weather/login.html",
        {"form": form},
    )

@require_POST
def logout_view(request):
    """Log out the current user and end their session."""
    logout(request)
    messages.success(request, "You have logged out successfully!")
    return redirect("home")

@login_required(login_url="login")
def favorites_view(request):
    favorites = FavoriteCity.objects.filter(
        user=request.user
    ).order_by("city")

    return render(
        request,
        "weather/favorites.html",
        {"favorites": favorites},
    )

@login_required(login_url="login")
@require_POST
def add_favorite_city(request):
    city = request.POST.get("city", "").strip()
    country = request.POST.get("country", "").strip().upper()

    if not city:
        messages.error(request, "Please provide a valid city.")
        return redirect("home")

    if len(city) > 100 or len(country) > 2:
        messages.error(request, "Invalid city or country.")
        return redirect("home")

    favorite, created = FavoriteCity.objects.get_or_create(
        user=request.user,
        city=city,
        country=country,
    )

    if created:
        messages.success(request, f"{city} added to your favorites.")
    else:
        messages.info(request, f"{city} is already in your favorites.")

    return redirect("home")

@login_required(login_url="login")
@require_POST
def remove_favorite_city(request, favorite_id):
    favorite = get_object_or_404(
        FavoriteCity,
        id=favorite_id,
        user=request.user,
    )

    city = favorite.city
    favorite.delete()

    messages.success(
        request,
        f"{city} removed from your favorites.",
    )

    return redirect("favorites")