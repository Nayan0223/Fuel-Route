from django.contrib import admin
from django.urls import include, path

from routing.views import RouteMapView

urlpatterns = [
    path("", RouteMapView.as_view(), name="route-map"),
    path("admin/", admin.site.urls),
    path("api/", include("routing.urls")),
]
