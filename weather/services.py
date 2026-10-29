import math
import time
import requests
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from .models import WeatherData

WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
REQUEST_TIMEOUT = getattr(settings, "WEATHER_API_TIMEOUT", 10)
MAX_RETRIES = 2
RETRY_BACKOFF = 1  # seconds between retries

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _openweathermap_request(url, params):
    """Call an OpenWeatherMap endpoint with retries and normalized error handling.

    Returns the parsed JSON dict on success, or {"error": <message>} on failure.
    All failure paths (timeout, connection error, HTTP error) return a consistent
    {"error": ...} dict so callers can handle errors uniformly.
    """
    last_error = "Unable to connect to the weather service."
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

            if response.status_code == 404:
                return {"error": "City not found."}

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            last_error = "Weather service request timed out."
            if attempt >= MAX_RETRIES:
                return {"error": last_error}
            time.sleep(RETRY_BACKOFF * (attempt + 1))
            continue

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in _RETRYABLE_STATUSES and attempt < MAX_RETRIES:
                last_error = f"Weather service error (HTTP {status}). Retrying..."
                time.sleep(RETRY_BACKOFF * (attempt + 1))
                continue
            last_error = (
                "Unable to connect to the weather service."
                if status is None
                else f"Weather service error (HTTP {status})."
            )
            return {"error": last_error}

        except requests.exceptions.RequestException:
            return {"error": "Unable to connect to the weather service."}

    return {"error": last_error}


def get_weather_data(city):
    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }
    return _openweathermap_request(WEATHER_BASE_URL, params)


def parse_weather_data(data):
    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "description": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
        "clouds": data["clouds"]["all"],
        "icon": data["weather"][0]["icon"],
    }


def get_forecast_data(city):
    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }
    return _openweathermap_request(FORECAST_BASE_URL, params)


def parse_forecast_data(data):
    forecast_list = []
    for entry in data["list"]:
        forecast_list.append({
            "datetime": entry["dt_txt"],
            "temperature": entry["main"]["temp"],
            "feels_like": entry["main"]["feels_like"],
            "humidity": entry["main"]["humidity"],
            "description": entry["weather"][0]["description"],
            "icon": entry["weather"][0]["icon"],
            "wind_speed": entry["wind"]["speed"],
            "clouds": entry["clouds"]["all"],
        })
    return {
        "city": data["city"]["name"],
        "country": data["city"]["country"],
        "forecast": forecast_list,
    }


def summarize_daily_forecast(parsed_forecast):
    daily_forecasts = {}

    for entry in parsed_forecast["forecast"]:
        day = entry["datetime"].split(" ")[0]

        if day not in daily_forecasts:
            daily_forecasts[day] = {
                "date": day,
                "temperatures": [],
                "description": entry["description"],
                "icon": entry["icon"],
            }

        daily_forecasts[day]["temperatures"].append(entry["temperature"])

    summaries = []

    for day_data in daily_forecasts.values():
        summaries.append({
            "date": day_data["date"],
            "min_temperature": min(day_data["temperatures"]),
            "max_temperature": max(day_data["temperatures"]),
            "description": day_data["description"],
            "icon": day_data["icon"],
        })

    return summaries


def calculate_forecast_statistics(parsed_forecast):
    """Calculate summary statistics from forecast data."""
    entries = parsed_forecast.get("forecast", [])

    if not entries:
        return {
            "avg_temperature": None,
            "max_temperature": None,
            "min_temperature": None,
            "avg_humidity": None,
            "avg_wind_speed": None,
        }

    temperatures = [entry["temperature"] for entry in entries]
    humidities = [entry["humidity"] for entry in entries]
    wind_speeds = [entry["wind_speed"] for entry in entries]

    return {
        "avg_temperature": round(sum(temperatures) / len(temperatures), 2),
        "max_temperature": max(temperatures),
        "min_temperature": min(temperatures),
        "avg_humidity": round(sum(humidities) / len(humidities), 2),
        "avg_wind_speed": round(sum(wind_speeds) / len(wind_speeds), 2),
    }


def _valid_numeric(value):
    """Return the numeric value if it is a real number, else None.

    Booleans and non-finite values (NaN, infinity) are rejected.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return value


def _format_timestamp(value):
    """Format a forecast datetime string, or return 'Time unavailable'."""
    if not isinstance(value, str):
        return "Time unavailable"
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Time unavailable"
    return dt.strftime("%b %d, %I:%M %p")


def generate_weather_insights(current_weather, parsed_forecast):
    """Generate weather insights from current weather and forecast data.

    Returns a dictionary with keys:
        temperature_trend, warmest_period, coolest_period,
        humidity_observation, forecast_summary
    """
    forecast = []
    if isinstance(parsed_forecast, dict):
        forecast = parsed_forecast.get("forecast", [])
    if not isinstance(forecast, list):
        forecast = []

    # Collect valid forecast temperatures with their entries, in forecast order.
    valid_entries = []
    for entry in forecast:
        temp = _valid_numeric(entry.get("temperature") if isinstance(entry, dict) else None)
        if temp is not None:
            valid_entries.append((entry, temp))

    # Temperature trend: compare first and last valid forecast temperatures.
    if len(valid_entries) < 2:
        temperature_trend = "Data unavailable"
    else:
        first_temp = valid_entries[0][1]
        last_temp = valid_entries[-1][1]
        if last_temp > first_temp:
            temperature_trend = "Rising"
        elif last_temp < first_temp:
            temperature_trend = "Falling"
        else:
            temperature_trend = "Stable"

    # Warmest and coolest periods (first match wins on ties).
    if not valid_entries:
        warmest_period = None
        coolest_period = None
    else:
        warmest = valid_entries[0]
        coolest = valid_entries[0]
        for entry, temp in valid_entries[1:]:
            if temp > warmest[1]:
                warmest = (entry, temp)
            if temp < coolest[1]:
                coolest = (entry, temp)
        warmest_period = {
            "temperature": warmest[1],
            "datetime": _format_timestamp(warmest[0].get("datetime")),
        }
        coolest_period = {
            "temperature": coolest[1],
            "datetime": _format_timestamp(coolest[0].get("datetime")),
        }

    # Humidity observation from current weather.
    humidity = None
    if isinstance(current_weather, dict):
        humidity = _valid_numeric(current_weather.get("humidity"))
    if humidity is None:
        humidity_observation = "Data unavailable"
    elif humidity < 30:
        humidity_observation = "Low"
    elif humidity <= 60:
        humidity_observation = "Comfortable"
    else:
        humidity_observation = "High"

    # Forecast summary: most frequent non-empty description (case-insensitive).
    # Ties resolve to the description that appeared first in the forecast.
    desc_counts = {}
    desc_order = []
    for entry in forecast:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description")
        if not isinstance(desc, str):
            continue
        desc = desc.strip()
        if not desc:
            continue
        key = desc.lower()
        if key not in desc_counts:
            desc_counts[key] = 0
            desc_order.append(key)
        desc_counts[key] += 1

    if desc_order:
        best_key = max(desc_order, key=lambda k: desc_counts[k])
        # Use the original-cased description from the first occurrence.
        forecast_summary = None
        for entry in forecast:
            if not isinstance(entry, dict):
                continue
            d = entry.get("description")
            if isinstance(d, str) and d.strip().lower() == best_key:
                forecast_summary = d.strip().title()
                break
    else:
        forecast_summary = "Data unavailable"

    return {
        "temperature_trend": temperature_trend,
        "warmest_period": warmest_period,
        "coolest_period": coolest_period,
        "humidity_observation": humidity_observation,
        "forecast_summary": forecast_summary,
    }


def save_weather_search(user, weather_data):
    """Create and return a WeatherData record from parsed weather data.

    Args:
        user: The user performing the search (may be None for anonymous).
        weather_data: Dict with keys city, country, temperature, feels_like,
            humidity, pressure, description, wind_speed, clouds.
    """
    return WeatherData.objects.create(
        user=user,
        city=weather_data["city"],
        country=weather_data["country"],
        temperature=weather_data["temperature"],
        feels_like=weather_data["feels_like"],
        humidity=weather_data["humidity"],
        pressure=weather_data["pressure"],
        description=weather_data["description"],
        wind_speed=weather_data["wind_speed"],
        clouds=weather_data["clouds"],
    )


def prepare_forecast_chart_data(parsed_forecast):
    """Return forecast chart labels and temperatures from parsed forecast data."""
    return {
        "labels": [
            entry["datetime"] for entry in parsed_forecast["forecast"]
        ],
        "temperatures": [
            entry["temperature"] for entry in parsed_forecast["forecast"]
        ],
    }


def prepare_humidity_chart_data(parsed_forecast):
    """Return humidity chart labels and humidities from parsed forecast data."""
    return {
        "labels": [
            entry["datetime"] for entry in parsed_forecast["forecast"]
        ],
        "humidities": [
            entry["humidity"] for entry in parsed_forecast["forecast"]
        ],
    }


def get_user_weather_history(user):
    """Return WeatherData queryset scoped to the given user."""
    if user and user.is_authenticated:
        return WeatherData.objects.filter(user=user)
    return WeatherData.objects.none()


def get_user_favorite_cities(user):
    """Return FavoriteCity queryset scoped to the given user, ordered by city."""
    from .models import FavoriteCity

    if user and user.is_authenticated:
        return FavoriteCity.objects.filter(user=user).order_by("city")
    return FavoriteCity.objects.none()


def analyze_weather_history(
    city=None,
    start_date=None,
    end_date=None,
    user=None,
):
    """Analyze historical weather data from saved WeatherData records.

    Filters records by city (case-insensitive) and date range, then computes
    temperature statistics and chart data from records with valid finite
    temperatures only. searched_at represents search time, not the weather
    API observation time.
    """
    queryset = WeatherData.objects.filter(user=user) if user is not None else WeatherData.objects.none()

    if city and city.strip():
        queryset = queryset.filter(city__iexact=city.strip())

    if start_date is not None:
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time())
        )
        queryset = queryset.filter(searched_at__gte=start_datetime)

    if end_date is not None:
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.min.time())
        ) + timedelta(days=1)
        queryset = queryset.filter(searched_at__lt=end_datetime)

    queryset = queryset.order_by("searched_at", "pk")

    city_name = city.strip() if city else ""
    # Evaluate the queryset once and reuse it, avoiding a separate count()
    # query plus a second query to iterate the records.
    records = list(queryset)
    record_count = len(records)

    valid_entries = []
    for record in records:
        temp = _valid_numeric(record.temperature)
        if temp is not None:
            valid_entries.append((record, temp))

    if valid_entries:
        temperatures = [temp for _, temp in valid_entries]
        min_temperature = min(temperatures)
        max_temperature = max(temperatures)
        avg_temperature = round(sum(temperatures) / len(temperatures), 2)
    else:
        min_temperature = None
        max_temperature = None
        avg_temperature = None

    chart_labels = []
    chart_temperatures = []
    for record, temp in valid_entries:
        chart_labels.append(record.searched_at.strftime("%b %d, %I:%M %p"))
        chart_temperatures.append(temp)

    return {
        "city": city_name,
        "start_date": start_date,
        "end_date": end_date,
        "record_count": record_count,
        "min_temperature": min_temperature,
        "max_temperature": max_temperature,
        "avg_temperature": avg_temperature,
        "chart_labels": chart_labels,
        "chart_temperatures": chart_temperatures,
    }
