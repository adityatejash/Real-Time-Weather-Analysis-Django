from django.contrib import admin

from .models import WeatherData, FavoriteCity, City


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = [
        "city",
        "country",
        "temperature",
        "humidity",
        "description",
        "searched_at",
        "user",
    ]
    list_filter = ["country", "searched_at", "user"]
    search_fields = ["city", "country", "description", "user__username"]
    ordering = ["-searched_at"]
    date_hierarchy = "searched_at"
    raw_id_fields = ["user"]
    readonly_fields = ["searched_at"]
    list_select_related = ["user"]

    fieldsets = [
        (
            "Location",
            {
                "fields": ["city", "country"],
            },
        ),
        (
            "Weather Measurements",
            {
                "fields": [
                    "temperature",
                    "feels_like",
                    "humidity",
                    "pressure",
                    "wind_speed",
                    "clouds",
                    "description",
                ],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["user", "searched_at"],
            },
        ),
    ]


@admin.register(FavoriteCity)
class FavoriteCityAdmin(admin.ModelAdmin):
    list_display = ["city", "country", "user", "created_at"]
    list_filter = ["country", "created_at", "user"]
    search_fields = ["city", "country", "user__username"]
    ordering = ["city"]
    raw_id_fields = ["user"]
    readonly_fields = ["created_at"]
    list_select_related = ["user"]
    date_hierarchy = "created_at"

    fieldsets = [
        (
            "Location",
            {
                "fields": ["city", "country"],
            },
        ),
        (
            "Metadata",
            {
                "fields": ["user", "created_at"],
            },
        ),
    ]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "region", "country", "population", "latitude", "longitude"]
    list_filter = ["country", "region"]
    search_fields = ["name", "region", "country"]
    ordering = ["-population", "name"]

    fieldsets = [
        (
            "Location",
            {
                "fields": ["name", "region", "country"],
            },
        ),
        (
            "Geography",
            {
                "fields": ["latitude", "longitude"],
            },
        ),
        (
            "Demographics",
            {
                "fields": ["population"],
            },
        ),
    ]
