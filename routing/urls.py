from django.urls import path

from routing.views import CitySearchView, RouteFuelView

urlpatterns = [
    path("cities/", CitySearchView.as_view(), name="city-search"),
    path("route/", RouteFuelView.as_view(), name="route-fuel"),
]
