from functools import lru_cache

from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from routing.models import FuelStation
from routing.services.fuel import build_route_profile, plan_fuel_stops
from routing.services.geo import parse_location, search_cities
from routing.services.map_features import build_map_feature_collection
from routing.services.osrm import RoutingError, fetch_route


@lru_cache(maxsize=1)
def get_geocoded_stations() -> tuple[FuelStation, ...]:
    return tuple(
        FuelStation.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    )


class RouteMapView(TemplateView):
    """Interactive map UI for planning routes and viewing fuel stops."""

    template_name = "routing/route_map.html"


class CitySearchView(APIView):
    """GET /api/cities/?q=new york — USA cities only."""

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"country": "USA", "results": []})
        return Response({"country": "USA", "results": search_cities(query)})


class RouteFuelView(APIView):
    """
    GET /api/route/?start=...&finish=...

    start/finish accept either 'lat,lng' coordinates or a US place name.
    Coordinates avoid geocoding API calls (1 OSRM call total).
    """

    def get(self, request: Request) -> Response:
        start_raw = request.query_params.get("start", "").strip()
        finish_raw = request.query_params.get("finish", "").strip()

        if not start_raw or not finish_raw:
            return Response(
                {"error": "Query parameters 'start' and 'finish' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = parse_location(start_raw)
            finish = parse_location(finish_raw)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            route = fetch_route(start, finish)
        except RoutingError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response(
                {"error": f"Routing service unavailable: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        stations = list(get_geocoded_stations())
        if not stations:
            return Response(
                {"error": "Fuel station data not loaded. Run: python manage.py import_fuel_stations"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        profile = build_route_profile(route["points"], route["distance_miles"])
        fuel_stops, fuel_summary = plan_fuel_stops(
            profile, route["distance_miles"], stations
        )
        fuel_stop_payload = [stop.to_dict() for stop in fuel_stops]
        route_properties = {
            "distance_miles": route["distance_miles"],
            "duration_seconds": route["duration_seconds"],
        }

        return Response(
            {
                "start": {"latitude": start[0], "longitude": start[1], "input": start_raw},
                "finish": {"latitude": finish[0], "longitude": finish[1], "input": finish_raw},
                "route": {
                    "type": "Feature",
                    "geometry": route["geometry"],
                    "properties": route_properties,
                },
                "fuel_stops": fuel_stop_payload,
                "fuel_summary": fuel_summary,
                "map": build_map_feature_collection(
                    route["geometry"],
                    route_properties,
                    start,
                    finish,
                    fuel_stop_payload,
                ),
            }
        )
