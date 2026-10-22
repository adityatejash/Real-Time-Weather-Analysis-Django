from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("history/", views.history_view, name="weather_history"),
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("favorites/", views.favorites_view, name="favorites"),
    path(
        "favorites/add/",
        views.add_favorite_city,
        name="add_favorite_city",
    ),
    path(
        "favorites/<int:favorite_id>/remove/",
        views.remove_favorite_city,
        name="remove_favorite_city",
    ),

]