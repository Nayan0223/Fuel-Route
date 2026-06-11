from dataclasses import dataclass

from django.conf import settings

from routing.models import FuelStation
from routing.services.geo import haversine_miles


@dataclass
class RoutePoint:
    latitude: float
    longitude: float
    distance_miles: float


@dataclass
class FuelStop:
    station: FuelStation
    route_mile: float
    gallons_purchased: float
    segment_cost_usd: float

    def to_dict(self) -> dict:
        return {
            "opis_id": self.station.opis_id,
            "name": self.station.name,
            "address": self.station.address,
            "city": self.station.city.strip(),
            "state": self.station.state,
            "retail_price": round(self.station.retail_price, 3),
            "latitude": self.station.latitude,
            "longitude": self.station.longitude,
            "route_mile": round(self.route_mile, 2),
            "gallons_purchased": round(self.gallons_purchased, 2),
            "segment_cost_usd": round(self.segment_cost_usd, 2),
        }


def build_route_profile(
    points: list[tuple[float, float]],
    total_distance_miles: float | None = None,
) -> list[RoutePoint]:
    if not points:
        return []

    # Downsample long routes to keep fuel planning fast.
    if len(points) > 800:
        step = max(1, len(points) // 800)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        points = sampled

    profile = [RoutePoint(points[0][0], points[0][1], 0.0)]
    for lat, lng in points[1:]:
        prev = profile[-1]
        step = haversine_miles(prev.latitude, prev.longitude, lat, lng)
        profile.append(RoutePoint(lat, lng, prev.distance_miles + step))

    if total_distance_miles and profile[-1].distance_miles > 0:
        scale = total_distance_miles / profile[-1].distance_miles
        profile = [
            RoutePoint(point.latitude, point.longitude, point.distance_miles * scale)
            for point in profile
        ]

    return profile


def point_at_mile(profile: list[RoutePoint], target_mile: float) -> RoutePoint:
    for point in profile:
        if point.distance_miles >= target_mile:
            return point
    return profile[-1]


def find_cheapest_station(
    latitude: float,
    longitude: float,
    stations: list[FuelStation],
    search_radius_miles: float,
) -> FuelStation | None:
    best: FuelStation | None = None
    best_price = float("inf")

    for station in stations:
        if station.latitude is None or station.longitude is None:
            continue
        distance = haversine_miles(
            latitude, longitude, station.latitude, station.longitude
        )
        if distance <= search_radius_miles and station.retail_price < best_price:
            best = station
            best_price = station.retail_price

    return best


def find_cheapest_near_route(
    profile: list[RoutePoint],
    stations: list[FuelStation],
    search_radius_miles: float,
) -> FuelStation | None:
    best: FuelStation | None = None
    best_price = float("inf")

    for point in profile[:: max(1, len(profile) // 200)]:
        station = find_cheapest_station(
            point.latitude, point.longitude, stations, search_radius_miles
        )
        if station and station.retail_price < best_price:
            best = station
            best_price = station.retail_price

    return best


def plan_fuel_stops(
    profile: list[RoutePoint],
    total_distance_miles: float,
    stations: list[FuelStation],
) -> tuple[list[FuelStop], dict]:
    max_range = settings.VEHICLE_MAX_RANGE_MILES
    mpg = settings.VEHICLE_MPG
    tank_gallons = max_range / mpg
    search_radius = settings.FUEL_SEARCH_RADIUS_MILES

    fuel_stops: list[FuelStop] = []
    total_cost = 0.0
    next_refuel_mile = max_range

    while next_refuel_mile < total_distance_miles:
        refuel_point = point_at_mile(profile, next_refuel_mile)
        station = find_cheapest_station(
            refuel_point.latitude,
            refuel_point.longitude,
            stations,
            search_radius,
        )
        if station is None:
            station = find_cheapest_near_route(profile, stations, search_radius * 2)
        if station is None:
            raise ValueError("No fuel stations found near the route.")

        miles_to_next_stop = min(max_range, total_distance_miles - next_refuel_mile)
        gallons = miles_to_next_stop / mpg
        segment_cost = gallons * station.retail_price
        total_cost += segment_cost

        fuel_stops.append(
            FuelStop(
                station=station,
                route_mile=next_refuel_mile,
                gallons_purchased=gallons,
                segment_cost_usd=segment_cost,
            )
        )

        next_refuel_mile += max_range

    total_gallons = total_distance_miles / mpg

    gallons_purchased = total_gallons

    if not fuel_stops:
        reference = find_cheapest_near_route(profile, stations, search_radius)
        if reference is None:
            raise ValueError("No fuel stations found near the route.")
        total_cost = total_gallons * reference.retail_price
        price_per_gallon = reference.retail_price
    else:
        gallons_purchased = sum(stop.gallons_purchased for stop in fuel_stops)
        price_per_gallon = total_cost / gallons_purchased if gallons_purchased else 0

    summary = {
        "total_distance_miles": round(total_distance_miles, 2),
        "mpg": mpg,
        "max_range_miles": max_range,
        "tank_capacity_gallons": round(tank_gallons, 2),
        "total_gallons_consumed": round(total_gallons, 2),
        "gallons_purchased": round(gallons_purchased, 2),
        "total_cost_usd": round(total_cost, 2),
        "average_price_per_gallon": round(price_per_gallon, 3),
        "fuel_stops_count": len(fuel_stops),
    }
    return fuel_stops, summary
