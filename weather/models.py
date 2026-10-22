from django.conf import settings
from django.db import models

# Create your models here.

class WeatherData(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weather_searches",
        null=True,
        blank=True,
    )
    city = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=2)
    temperature = models.FloatField()
    feels_like = models.FloatField()
    humidity = models.IntegerField()
    pressure = models.IntegerField()
    description = models.CharField(max_length=255)
    wind_speed = models.FloatField()
    clouds = models.IntegerField()
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-searched_at"]

    def __str__(self):
        return f"{self.city}, {self.country}"


class FavoriteCity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_cities",
    )
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=2, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["city"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "city", "country"],
                name="unique_favorite_city_per_user",
            )
        ]

    def __str__(self):
        return f"{self.city}, {self.country}" if self.country else self.city
