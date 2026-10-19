from django.test import TestCase
from unittest.mock import patch
from django.test import Client
from django.urls import reverse


class WeatherChartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('home')

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_successful_city_search_passes_chart_data(self, mock_get_forecast, mock_get_weather):
        # Mock successful weather API response
        mock_get_weather.return_value = {
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": 20.0,
                "feels_like": 19.5,
                "humidity": 50,
                "pressure": 1015
            },
            "wind": {"speed": 3.5},
            "clouds": {"all": 20},
            "name": "London",
            "sys": {"country": "GB"}
        }
        # Mock successful forecast API response with 3 forecast items
        # Each item must have the fields expected by parse_forecast_data
        mock_get_forecast.return_value = {
            "list": [
                {
                    "dt": 1610000000,
                    "dt_txt": "2021-01-07 12:00:00",
                    "main": {
                        "temp": 22.0,
                        "feels_like": 21.5,
                        "humidity": 60
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 3.0},
                    "clouds": {"all": 20}
                },
                {
                    "dt": 1610003600,
                    "dt_txt": "2021-01-07 15:00:00",
                    "main": {
                        "temp": 23.0,
                        "feels_like": 22.5,
                        "humidity": 55
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 3.5},
                    "clouds": {"all": 15}
                },
                {
                    "dt": 1610007200,
                    "dt_txt": "2021-01-07 18:00:00",
                    "main": {
                        "temp": 21.0,
                        "feels_like": 20.5,
                        "humidity": 50
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 4.0},
                    "clouds": {"all": 10}
                }
            ],
            "city": {
                "name": "London",
                "country": "GB"
            }
        }

        response = self.client.get(self.url, {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        # Check that forecast_chart is in the context
        self.assertIn('forecast_chart', response.context)
        forecast_chart = response.context['forecast_chart']
        self.assertIsNotNone(forecast_chart)
        # Check that labels and temperatures are present and have correct length
        self.assertEqual(len(forecast_chart['labels']), 3)
        self.assertEqual(len(forecast_chart['temperatures']), 3)
        # Check that the labels match the dt_txt values from the mock
        expected_labels = ["2021-01-07 12:00:00", "2021-01-07 15:00:00", "2021-01-07 18:00:00"]
        self.assertEqual(list(forecast_chart['labels']), expected_labels)
        # Check that temperatures match the temp values from the mock
        expected_temps = [22.0, 23.0, 21.0]
        self.assertEqual(list(forecast_chart['temperatures']), expected_temps)

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_forecast_api_error_no_chart_data(self, mock_get_forecast, mock_get_weather):
        # Mock successful weather API response
        mock_get_weather.return_value = {
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": 20.0,
                "feels_like": 19.5,
                "humidity": 50,
                "pressure": 1015
            },
            "wind": {"speed": 3.5},
            "clouds": {"all": 20},
            "name": "London",
            "sys": {"country": "GB"}
        }
        # Mock forecast API returning an error
        mock_get_forecast.return_value = {"error": "API error"}

        response = self.client.get(self.url, {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        # Check that forecast_chart is in the context but is None
        self.assertIn('forecast_chart', response.context)
        forecast_chart = response.context['forecast_chart']
        self.assertIsNone(forecast_chart)
        # Also check that forecast_error is set
        self.assertIn('forecast_error', response.context)
        self.assertIsNotNone(response.context['forecast_error'])
