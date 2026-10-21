from django.test import TestCase
from unittest.mock import patch
from django.test import Client
from django.urls import reverse

from weather.services import generate_weather_insights


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
        # Humidity chart assertions
        humidity_chart = response.context["humidity_chart"]
        self.assertIsNotNone(humidity_chart)
        self.assertEqual(
            list(humidity_chart["labels"]),
            expected_labels,
        )
        self.assertEqual(
            list(humidity_chart["humidities"]),
            [60, 55, 50],
        )

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


class WeatherInsightsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('home')

    def _forecast(self, entries):
        return {"forecast": entries}

    def test_temperature_trend_rising(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 23.0, "description": "clear sky"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Rising")

    def test_temperature_trend_falling(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 23.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 20.0, "description": "clear sky"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Falling")

    def test_temperature_trend_stable(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 20.0, "description": "clear sky"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Stable")

    def test_temperature_trend_data_unavailable_when_fewer_than_two_valid(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Data unavailable")

    def test_warmest_period(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 25.0, "description": "cloudy"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 22.0, "description": "rain"},
            ]),
        )
        self.assertEqual(
            result["warmest_period"],
            {"temperature": 25.0, "datetime": "Jan 07, 03:00 PM"},
        )

    def test_coolest_period(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 25.0, "description": "cloudy"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 18.0, "description": "rain"},
            ]),
        )
        self.assertEqual(
            result["coolest_period"],
            {"temperature": 18.0, "datetime": "Jan 07, 06:00 PM"},
        )

    def test_warmest_period_first_occurrence_wins_tie(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 25.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 25.0, "description": "cloudy"},
            ]),
        )
        self.assertEqual(result["warmest_period"]["datetime"], "Jan 07, 12:00 PM")

    def test_coolest_period_first_occurrence_wins_tie(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 18.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 18.0, "description": "cloudy"},
            ]),
        )
        self.assertEqual(result["coolest_period"]["datetime"], "Jan 07, 12:00 PM")

    def test_warmest_and_coolest_none_when_no_valid_forecast(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": None, "description": "clear sky"},
            ]),
        )
        self.assertIsNone(result["warmest_period"])
        self.assertIsNone(result["coolest_period"])

    def test_humidity_observation_low(self):
        result = generate_weather_insights({"humidity": 20}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "Low")

    def test_humidity_observation_comfortable(self):
        result = generate_weather_insights({"humidity": 30}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "Comfortable")
        result = generate_weather_insights({"humidity": 60}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "Comfortable")

    def test_humidity_observation_high(self):
        result = generate_weather_insights({"humidity": 70}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "High")

    def test_humidity_observation_data_unavailable(self):
        result = generate_weather_insights({}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "Data unavailable")
        result = generate_weather_insights({"humidity": None}, self._forecast([]))
        self.assertEqual(result["humidity_observation"], "Data unavailable")

    def test_forecast_summary_most_frequent(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 21.0, "description": "clear sky"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 22.0, "description": "cloudy"},
            ]),
        )
        self.assertEqual(result["forecast_summary"], "Clear Sky")

    def test_forecast_summary_case_insensitive(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "Clear Sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 21.0, "description": "clear sky"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 22.0, "description": "CLEAR SKY"},
            ]),
        )
        self.assertEqual(result["forecast_summary"], "Clear Sky")

    def test_forecast_summary_title_capitalization(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "light rain"},
            ]),
        )
        self.assertEqual(result["forecast_summary"], "Light Rain")

    def test_forecast_summary_first_occurrence_wins_tie(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "cloudy"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 21.0, "description": "clear sky"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 22.0, "description": "cloudy"},
                {"datetime": "2021-01-07 21:00:00", "temperature": 23.0, "description": "clear sky"},
            ]),
        )
        # cloudy and clear sky both appear twice; cloudy appears first
        self.assertEqual(result["forecast_summary"], "Cloudy")

    def test_forecast_summary_data_unavailable(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": ""},
                {"datetime": "2021-01-07 15:00:00", "temperature": 21.0, "description": None},
            ]),
        )
        self.assertEqual(result["forecast_summary"], "Data unavailable")

    def test_forecast_summary_empty_forecast(self):
        result = generate_weather_insights({"humidity": 50}, {})
        self.assertEqual(result["forecast_summary"], "Data unavailable")

    def test_boolean_temperature_rejected(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": True, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 20.0, "description": "clear sky"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Data unavailable")
        self.assertEqual(result["warmest_period"]["temperature"], 20.0)

    def test_nan_inf_temperatures_rejected(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": float("nan"), "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": float("inf"), "description": "cloudy"},
                {"datetime": "2021-01-07 18:00:00", "temperature": 20.0, "description": "rain"},
            ]),
        )
        self.assertEqual(result["temperature_trend"], "Data unavailable")
        self.assertEqual(result["warmest_period"]["temperature"], 20.0)

    def test_boolean_humidity_rejected(self):
        result = generate_weather_insights(
            {"humidity": True},
            self._forecast([]),
        )
        self.assertEqual(result["humidity_observation"], "Data unavailable")

    def test_all_return_keys_present(self):
        result = generate_weather_insights(
            {"humidity": 50},
            self._forecast([
                {"datetime": "2021-01-07 12:00:00", "temperature": 20.0, "description": "clear sky"},
                {"datetime": "2021-01-07 15:00:00", "temperature": 25.0, "description": "cloudy"},
            ]),
        )
        self.assertEqual(
            set(result.keys()),
            {
                "temperature_trend",
                "warmest_period",
                "coolest_period",
                "humidity_observation",
                "forecast_summary",
            },
        )

    def test_none_inputs(self):
        result = generate_weather_insights(None, None)
        self.assertEqual(result["temperature_trend"], "Data unavailable")
        self.assertIsNone(result["warmest_period"])
        self.assertIsNone(result["coolest_period"])
        self.assertEqual(result["humidity_observation"], "Data unavailable")
        self.assertEqual(result["forecast_summary"], "Data unavailable")

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_home_view_provides_insights(self, mock_get_forecast, mock_get_weather):
        mock_get_weather.return_value = {
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": 20.0,
                "feels_like": 19.5,
                "humidity": 50,
                "pressure": 1015,
            },
            "wind": {"speed": 3.5},
            "clouds": {"all": 20},
            "name": "London",
            "sys": {"country": "GB"},
        }
        mock_get_forecast.return_value = {
            "list": [
                {
                    "dt": 1610000000,
                    "dt_txt": "2021-01-07 12:00:00",
                    "main": {
                        "temp": 22.0,
                        "feels_like": 21.5,
                        "humidity": 60,
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 3.0},
                    "clouds": {"all": 20},
                },
                {
                    "dt": 1610003600,
                    "dt_txt": "2021-01-07 15:00:00",
                    "main": {
                        "temp": 23.0,
                        "feels_like": 22.5,
                        "humidity": 55,
                    },
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                    "wind": {"speed": 3.5},
                    "clouds": {"all": 15},
                },
            ],
            "city": {"name": "London", "country": "GB"},
        }

        response = self.client.get(self.url, {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('insights', response.context)
        insights = response.context['insights']
        self.assertIsNotNone(insights)
        self.assertEqual(
            set(insights.keys()),
            {
                "temperature_trend",
                "warmest_period",
                "coolest_period",
                "humidity_observation",
                "forecast_summary",
            },
        )

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_home_view_forecast_error_still_provides_insights(
        self, mock_get_forecast, mock_get_weather
    ):
        mock_get_weather.return_value = {
            "weather": [{"description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": 20.0,
                "feels_like": 19.5,
                "humidity": 50,
                "pressure": 1015,
            },
            "wind": {"speed": 3.5},
            "clouds": {"all": 20},
            "name": "London",
            "sys": {"country": "GB"},
        }
        mock_get_forecast.return_value = {"error": "API error"}

        response = self.client.get(self.url, {'city': 'London'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('insights', response.context)
        insights = response.context['insights']
        self.assertIsNotNone(insights)
        # Forecast-related values are unavailable when the forecast API fails.
        self.assertEqual(insights["temperature_trend"], "Data unavailable")
        self.assertIsNone(insights["warmest_period"])
        self.assertIsNone(insights["coolest_period"])
        self.assertEqual(insights["forecast_summary"], "Data unavailable")
        # Humidity observation still comes from current weather.
        self.assertEqual(insights["humidity_observation"], "Comfortable")
