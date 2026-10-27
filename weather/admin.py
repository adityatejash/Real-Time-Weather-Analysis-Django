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


@admin.register(FavoriteCity)
class FavoriteCityAdmin(admin.ModelAdmin):
    list_display = ["city", "country", "user", "created_at"]
    list_filter = ["country", "created_at", "user"]
    search_fields = ["city", "country", "user__username"]
    ordering = ["city"]
    raw_id_fields = ["user"]


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "region", "country", "population", "latitude", "longitude"]
    list_filter = ["country", "region"]
    search_fields = ["name", "region", "country"]
    ordering = ["-population", "name"]
