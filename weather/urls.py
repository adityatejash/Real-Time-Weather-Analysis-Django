from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("cities/autocomplete/", views.city_autocomplete, name="city_autocomplete"),
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

    # Error pages (exposed for direct access and testing).
    path("404/", views.page_not_found, name="page_not_found"),
    path("500/", views.server_error, name="server_error"),
    path("403/", views.permission_denied, name="permission_denied"),
    path("400/", views.bad_request, name="bad_request"),

]