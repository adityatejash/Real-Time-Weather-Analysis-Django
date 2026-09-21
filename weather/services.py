import requests

from django.conf import settings


BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather_data(city):
    params = {
        "q": city,
        "appid": settings.WEATHER_API_KEY,
        "units": "metric",
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()