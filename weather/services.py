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