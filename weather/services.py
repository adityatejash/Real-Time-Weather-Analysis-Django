import requests

from django.conf import settings


BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_data(city):
    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=10,
        )

        if response.status_code == 404:
            return {
                "error": "City not found."
            }

        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        return {
            "error": "Weather service request timed out."
        }

    except requests.exceptions.RequestException:
        return {
            "error": "Unable to connect to the weather service."
        }


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
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(
            forecast_url,
            params=params,
            timeout=10,
        )

        if response.status_code == 404:
            return {
                "error": "City not found."
            }

        response.raise_for_status()

        return response.json()

    except requests.exceptions.Timeout:
        return {
            "error": "Weather service request timed out."
        }

    except requests.exceptions.RequestException:
        return {
            "error": "Unable to connect to the weather service."
        }


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
