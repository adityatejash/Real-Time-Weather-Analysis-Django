import secrets
from datetime import date, datetime
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from weather.models import WeatherData
from weather.services import analyze_weather_history, generate_weather_insights


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


@override_settings(TIME_ZONE="UTC")
class WeatherHistoryAnalysisTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="history_analysis_user",
            password=secrets.token_urlsafe(32),
        )
        self.t1 = timezone.make_aware(datetime(2026, 1, 15, 10, 0, 0))
        self.t2 = timezone.make_aware(datetime(2026, 1, 15, 14, 0, 0))
        self.t3 = timezone.make_aware(datetime(2026, 1, 16, 10, 0, 0))
        self.t4 = timezone.make_aware(datetime(2026, 1, 16, 16, 0, 0))

        r1 = WeatherData.objects.create(
            user=self.user,
            city="London", country="GB", temperature=10.0, feels_like=9.0,
            humidity=60, pressure=1015, description="clear sky",
            wind_speed=3.5, clouds=20,
        )
        r2 = WeatherData.objects.create(
            user=self.user,
            city="London", country="GB", temperature=15.0, feels_like=14.0,
            humidity=55, pressure=1013, description="partly cloudy",
            wind_speed=4.0, clouds=40,
        )
        r3 = WeatherData.objects.create(
            user=self.user,
            city="london", country="GB", temperature=20.0, feels_like=19.0,
            humidity=50, pressure=1010, description="rain",
            wind_speed=5.0, clouds=90,
        )
        r4 = WeatherData.objects.create(
            user=self.user,
            city="Paris", country="FR", temperature=5.0, feels_like=4.0,
            humidity=70, pressure=1020, description="snow",
            wind_speed=2.0, clouds=100,
        )

        # searched_at has auto_now_add=True, so override via update() which
        # bypasses save() and lets us set explicit historical timestamps.
        WeatherData.objects.filter(pk=r1.pk).update(searched_at=self.t1)
        WeatherData.objects.filter(pk=r2.pk).update(searched_at=self.t2)
        WeatherData.objects.filter(pk=r3.pk).update(searched_at=self.t3)
        WeatherData.objects.filter(pk=r4.pk).update(searched_at=self.t4)

    def test_multiple_records_statistics_and_chart(self):
        result = analyze_weather_history(user=self.user)
        self.assertEqual(result["city"], "")
        self.assertIsNone(result["start_date"])
        self.assertIsNone(result["end_date"])
        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["min_temperature"], 5.0)
        self.assertEqual(result["max_temperature"], 20.0)
        self.assertEqual(result["avg_temperature"], 12.5)
        self.assertEqual(
            result["chart_labels"],
            ["Jan 15, 10:00 AM", "Jan 15, 02:00 PM", "Jan 16, 10:00 AM", "Jan 16, 04:00 PM"],
        )
        self.assertEqual(result["chart_temperatures"], [10.0, 15.0, 20.0, 5.0])

    def test_city_filtering_case_insensitive(self):
        result = analyze_weather_history(city="LONDON", user=self.user)
        self.assertEqual(result["city"], "LONDON")
        self.assertEqual(result["record_count"], 3)
        self.assertEqual(result["min_temperature"], 10.0)
        self.assertEqual(result["max_temperature"], 20.0)
        self.assertEqual(result["avg_temperature"], 15.0)

    def test_city_filtering_trims_whitespace(self):
        result = analyze_weather_history(city="  london  ", user=self.user)
        self.assertEqual(result["city"], "london")
        self.assertEqual(result["record_count"], 3)

    def test_start_date_filtering_includes_start_date(self):
        result = analyze_weather_history(
            start_date=date(2026, 1, 15),
            user=self.user,
        )
        self.assertEqual(result["record_count"], 4)
        self.assertEqual(result["start_date"], date(2026, 1, 15))

    def test_start_date_filtering_excludes_before_start(self):
        result = analyze_weather_history(
            start_date=date(2026, 1, 16),
            user=self.user,
        )
        self.assertEqual(result["record_count"], 2)

    def test_end_date_filtering_includes_entire_end_date(self):
        result = analyze_weather_history(
            end_date=date(2026, 1, 15),
            user=self.user,
        )
        self.assertEqual(result["record_count"], 2)

    def test_end_date_filtering_excludes_after_end(self):
        result = analyze_weather_history(
            end_date=date(2026, 1, 16),
            user=self.user,
        )
        self.assertEqual(result["record_count"], 4)

    def test_combined_city_and_date_filtering(self):
        result = analyze_weather_history(
            city="Paris",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 16),
            user=self.user,
        )
        self.assertEqual(result["city"], "Paris")
        self.assertEqual(result["record_count"], 1)
        self.assertEqual(result["min_temperature"], 5.0)
        self.assertEqual(result["max_temperature"], 5.0)
        self.assertEqual(result["avg_temperature"], 5.0)

    def test_empty_results(self):
        result = analyze_weather_history(city="Berlin", user=self.user)
        self.assertEqual(result["city"], "Berlin")
        self.assertEqual(result["record_count"], 0)
        self.assertIsNone(result["min_temperature"])
        self.assertIsNone(result["max_temperature"])
        self.assertIsNone(result["avg_temperature"])
        self.assertEqual(result["chart_labels"], [])
        self.assertEqual(result["chart_temperatures"], [])


class WeatherHistoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        User = get_user_model()
        self.user = User.objects.create_user(
            username="history_view_user",
            password=secrets.token_urlsafe(32),
        )
        self.client.force_login(self.user)

        self.url = reverse("weather_history")

        self.t1 = timezone.make_aware(datetime(2026, 1, 15, 10, 0, 0))
        self.t2 = timezone.make_aware(datetime(2026, 1, 15, 14, 0, 0))
        self.t3 = timezone.make_aware(datetime(2026, 1, 16, 10, 0, 0))
        self.t4 = timezone.make_aware(datetime(2026, 1, 16, 16, 0, 0))

        r1 = WeatherData.objects.create(
            user=self.user,
            city="London", country="GB", temperature=10.0, feels_like=9.0,
            humidity=60, pressure=1015, description="clear sky",
            wind_speed=3.5, clouds=20,
        )
        r2 = WeatherData.objects.create(
            user=self.user,
            city="London", country="GB", temperature=15.0, feels_like=14.0,
            humidity=55, pressure=1013, description="partly cloudy",
            wind_speed=4.0, clouds=40,
        )
        r3 = WeatherData.objects.create(
            user=self.user,
            city="london", country="GB", temperature=20.0, feels_like=19.0,
            humidity=50, pressure=1010, description="rain",
            wind_speed=5.0, clouds=90,
        )
        r4 = WeatherData.objects.create(
            user=self.user,
            city="Paris", country="FR", temperature=5.0, feels_like=4.0,
            humidity=70, pressure=1020, description="snow",
            wind_speed=2.0, clouds=100,
        )

        # searched_at has auto_now_add=True, so override via update()
        WeatherData.objects.filter(pk=r1.pk).update(searched_at=self.t1)
        WeatherData.objects.filter(pk=r2.pk).update(searched_at=self.t2)
        WeatherData.objects.filter(pk=r3.pk).update(searched_at=self.t3)
        WeatherData.objects.filter(pk=r4.pk).update(searched_at=self.t4)

    def test_page_loads_successfully(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "weather/history.html")

    def test_named_url_resolves(self):
        self.assertEqual(reverse("weather_history"), "/history/")

    def test_filters_passed_to_service(self):
        with patch("weather.views.analyze_weather_history") as mock_service:
            mock_service.return_value = {
                "city": "London",
                "start_date": date(2026, 1, 15),
                "end_date": date(2026, 1, 16),
                "record_count": 0,
                "min_temperature": None,
                "max_temperature": None,
                "avg_temperature": None,
                "chart_labels": [],
                "chart_temperatures": [],
            }
            response = self.client.get(
                self.url,
                {"city": "London", "start_date": "2026-01-15", "end_date": "2026-01-16"},
            )
        self.assertEqual(response.status_code, 200)
        mock_service.assert_called_once_with(
    "London",
    date(2026, 1, 15),
    date(2026, 1, 16),
    user=self.user,
)

    def test_valid_filters_appear_in_response(self):
        response = self.client.get(
            self.url,
            {"city": "London", "start_date": "2026-01-15", "end_date": "2026-01-16"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["city"], "London")
        self.assertEqual(response.context["start_date"], "2026-01-15")
        self.assertEqual(response.context["end_date"], "2026-01-16")
        self.assertContains(response, "London")

    def test_invalid_date_no_server_error(self):
        response = self.client.get(self.url, {"start_date": "not-a-date"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["result"])
        self.assertIsNotNone(response.context["validation_error"])
        self.assertContains(response, "Invalid filters")

    def test_start_date_later_than_end_date(self):
        response = self.client.get(
            self.url,
            {"start_date": "2026-01-20", "end_date": "2026-01-15"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["result"])
        self.assertIsNotNone(response.context["validation_error"])
        self.assertIn(
            "Start date cannot be later",
            response.context["validation_error"],
        )

    def test_empty_results_display_empty_state(self):
        response = self.client.get(self.url, {"city": "Berlin"})
        self.assertEqual(response.status_code, 200)
        result = response.context["result"]
        self.assertEqual(result["record_count"], 0)
        self.assertContains(response, "No weather records match your filters")

    def test_summary_and_chart_data_rendered(self):
        response = self.client.get(
            self.url,
            {"city": "London", "start_date": "2026-01-15", "end_date": "2026-01-16"},
        )
        self.assertEqual(response.status_code, 200)
        result = response.context["result"]
        self.assertGreater(result["record_count"], 0)
        self.assertIsNotNone(result["min_temperature"])
        self.assertIsNotNone(result["max_temperature"])
        self.assertIsNotNone(result["avg_temperature"])
        self.assertGreater(len(result["chart_labels"]), 0)
        self.assertGreater(len(result["chart_temperatures"]), 0)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class AuthenticationConfigurationTests(TestCase):
    """Tests verifying Django authentication is properly configured.

    These tests guard the authentication foundation established by WT-033:
    required auth/session/contenttypes/messages apps, required middleware,
    password validators, default User model, default auth backend, and the
    auth context processor.
    """

    def test_auth_app_installed(self):
        from django.conf import settings
        self.assertIn('django.contrib.auth', settings.INSTALLED_APPS)

    def test_contenttypes_app_installed(self):
        from django.conf import settings
        self.assertIn('django.contrib.contenttypes', settings.INSTALLED_APPS)

    def test_sessions_app_installed(self):
        from django.conf import settings
        self.assertIn('django.contrib.sessions', settings.INSTALLED_APPS)

    def test_messages_app_installed(self):
        from django.conf import settings
        self.assertIn('django.contrib.messages', settings.INSTALLED_APPS)

    def test_authentication_middleware_configured(self):
        from django.conf import settings
        self.assertIn(
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            settings.MIDDLEWARE,
        )

    def test_session_middleware_configured(self):
        from django.conf import settings
        self.assertIn(
            'django.contrib.sessions.middleware.SessionMiddleware',
            settings.MIDDLEWARE,
        )

    def test_csrf_middleware_configured(self):
        from django.conf import settings
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE,
        )

    def test_messages_middleware_configured(self):
        from django.conf import settings
        self.assertIn(
            'django.contrib.messages.middleware.MessageMiddleware',
            settings.MIDDLEWARE,
        )

    def test_password_validators_configured(self):
        from django.conf import settings
        validator_names = [v['NAME'] for v in settings.AUTH_PASSWORD_VALIDATORS]
        expected = [
            'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
            'django.contrib.auth.password_validation.MinimumLengthValidator',
            'django.contrib.auth.password_validation.CommonPasswordValidator',
            'django.contrib.auth.password_validation.NumericPasswordValidator',
        ]
        for name in expected:
            self.assertIn(name, validator_names)

    def test_default_user_model(self):
        from django.conf import settings
        self.assertEqual(settings.AUTH_USER_MODEL, 'auth.User')

    def test_default_authentication_backend(self):
        from django.conf import settings
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            ['django.contrib.auth.backends.ModelBackend'],
        )

    def test_auth_context_processor_configured(self):
        from django.conf import settings
        context_processors = settings.TEMPLATES[0]['OPTIONS']['context_processors']
        self.assertIn(
            'django.contrib.auth.context_processors.auth',
            context_processors,
        )


class AuthenticationFunctionalTests(TestCase):
    """Functional tests verifying Django authentication behavior end to end."""

    def setUp(self):
        self.User = get_user_model()
        self.test_password = secrets.token_urlsafe(32)
        self.user = self.User.objects.create_user(
            username='testuser',
            password=self.test_password,
        )

    def test_create_user_authenticate_success_and_failure(self):
        # Correct password authenticates successfully.
        user = authenticate(
            username='testuser',
            password=self.test_password,
        )
        self.assertIsNotNone(user)
        self.assertEqual(user, self.user)

        # An independently generated incorrect password fails authentication.
        user = authenticate(
            username='testuser',
            password=secrets.token_urlsafe(32),
        )
        self.assertIsNone(user)

    def test_client_login_authenticated_user(self):
        # Test client can log in.
        self.assertTrue(
            self.client.login(
                username='testuser',
                password=self.test_password,
            )
        )

        # Access a public page and verify request.user is authenticated.
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'], self.user)


from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from unittest.mock import patch


class WeatherSearchOwnershipTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user_a = User.objects.create_user(
            username="search_user_a",
            password="TestPassword123!",
        )
        self.user_b = User.objects.create_user(
            username="search_user_b",
            password="TestPassword123!",
        )
        self.client = Client()

    @patch("weather.views.get_weather_data")
    def test_saved_search_is_associated_with_logged_in_user(
        self, mock_get_weather_data
    ):
        # Update the mock response to match the structure expected
        # by your existing home() view and parse_weather_data().
        mock_get_weather_data.return_value = {
            "name": "London",
            "sys": {"country": "GB"},
            "main": {
                "temp": 15.0,
                "feels_like": 14.0,
                "humidity": 60,
                "pressure": 1015,
            },
            "weather": [
                {
                    "description": "clear sky",
                    "icon": "01d",
                }
            ],
            "wind": {"speed": 3.5},
            "clouds": {"all": 20},
        }

        self.client.force_login(self.user_a)

        # Adapt the URL and request method to your home() view.
        response = self.client.get("/", {"city": "London"})

        self.assertEqual(response.status_code, 200)

        from weather.models import WeatherData

        saved_search = WeatherData.objects.filter(city__iexact="London").latest(
            "searched_at"
        )
        self.assertEqual(saved_search.user, self.user_a)

    def test_different_users_have_separate_saved_searches(self):
        from weather.models import WeatherData

        search_a = WeatherData.objects.create(
            user=self.user_a,
            city="London",
            country="GB",
            temperature=15.0,
            feels_like=14.0,
            humidity=60,
            pressure=1015,
            description="clear sky",
            wind_speed=3.5,
            clouds=20,
        )

        search_b = WeatherData.objects.create(
            user=self.user_b,
            city="Tokyo",
            country="JP",
            temperature=20.0,
            feels_like=19.0,
            humidity=50,
            pressure=1010,
            description="clear sky",
            wind_speed=2.5,
            clouds=10,
        )

        self.assertEqual(
            list(WeatherData.objects.filter(user=self.user_a)),
            [search_a],
        )
        self.assertEqual(
            list(WeatherData.objects.filter(user=self.user_b)),
            [search_b],
        )


class WeatherSearchExperienceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('home')

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_error_message_rendered_inline_in_search_section(
        self, mock_get_forecast, mock_get_weather
    ):
        """TC-019: Error message appears inline in search section when API returns error."""
        mock_get_weather.return_value = {"error": "City not found."}
        mock_get_forecast.return_value = {"error": "City not found."}

        response = self.client.get(self.url, {'city': 'Nowhere'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('error', response.context)
        self.assertEqual(response.context['error'], "City not found.")
        self.assertContains(response, "City not found.")
        self.assertContains(response, 'id="searchError"')

    @patch('weather.views.get_weather_data')
    @patch('weather.views.get_forecast_data')
    def test_recent_searches_rendered_as_chips(
        self, mock_get_forecast, mock_get_weather
    ):
        """TC-020: Recent searches appear as quick-select chips."""
        User = get_user_model()
        user = User.objects.create_user(username="recent_user", password="testpass123")

        WeatherData.objects.create(
            user=user,
            city="London", country="GB", temperature=15.0, feels_like=14.0,
            humidity=60, pressure=1015, description="clear sky",
            wind_speed=3.5, clouds=20,
        )
        WeatherData.objects.create(
            user=user,
            city="Paris", country="FR", temperature=20.0, feels_like=19.0,
            humidity=55, pressure=1013, description="partly cloudy",
            wind_speed=4.0, clouds=40,
        )

        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('latest_searches', response.context)
        self.assertEqual(len(response.context['latest_searches']), 2)
        self.assertContains(response, "London")
        self.assertContains(response, "Paris")
        self.assertContains(response, 'recent-search-chip')
