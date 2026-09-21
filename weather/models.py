from django.db import models

# Create your models here.

class WeatherData(models.Model):
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

    def __str__(self):
        return f"{self.city}, {self.country}"