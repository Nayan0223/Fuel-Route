from functools import lru_cache

import requests
from django.conf import settings

from routing.services.geo import meters_to_miles

MAX_ROUTE_COORDINATES = 600


class RoutingError(Exception):
    pass


def simplify_geometry(geometry: dict, max_points: int = MAX_ROUTE_COORDINATES) -> dict:
    coordinates = geometry.get("coordinates", [])
    if len(coordinates) <= max_points:
        return geometry

    step = max(1, len(coordinates) // max_points)
    simplified = coordinates[::step]
    if simplified[-1] != coordinates[-1]:
        simplified.append(coordinates[-1])

    return {"type": geometry["type"], "coordinates": simplified}


@lru_cache(maxsize=64)
def fetch_route(start: tuple[float, float], end: tuple[float, float]) -> dict:
    """
    Fetch a driving route from OSRM in a single API call.
    Returns GeoJSON geometry, distance in miles, duration, and sampled points.
    """
    start_lng, start_lat = start[1], start[0]
    end_lng, end_lat = end[1], end[0]
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(payload.get("message", "Routing failed"))

    route = payload["routes"][0]
    full_coordinates = route["geometry"]["coordinates"]
    points = [(coord[1], coord[0]) for coord in full_coordinates]
    geometry = simplify_geometry(route["geometry"])

    return {
        "geometry": geometry,
        "distance_miles": round(meters_to_miles(route["distance"]), 2),
        "duration_seconds": round(route["duration"]),
        "points": points,
    }
