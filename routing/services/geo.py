import csv
import math
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from geopy.geocoders import Nominatim

MILES_PER_METER = 1 / 1609.344
EARTH_RADIUS_MILES = 3958.8

# Rough bounding regions for the United States (continental US, Alaska, Hawaii).
USA_REGIONS = (
    (24.396308, 49.384358, -124.848974, -66.885444),
    (51.0, 71.5, -179.0, -129.0),
    (18.0, 23.0, -161.0, -154.0),
)


def normalize_city(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().upper())


def is_within_usa(latitude: float, longitude: float) -> bool:
    for min_lat, max_lat, min_lng, max_lng in USA_REGIONS:
        if min_lat <= latitude <= max_lat and min_lng <= longitude <= max_lng:
            return True
    return False


def validate_usa_location(latitude: float, longitude: float, label: str = "Location") -> None:
    if not is_within_usa(latitude, longitude):
        raise ValueError(f"{label} must be within the United States.")


@lru_cache(maxsize=1)
def _load_city_records() -> tuple[dict, ...]:
    records = []
    seen: set[tuple[str, str]] = set()
    path = Path(settings.US_CITIES_CSV)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            city = row["CITY"].strip()
            state_code = row["STATE_CODE"].upper()
            key = (normalize_city(city), state_code)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "city": city,
                    "state": state_code,
                    "state_name": row["STATE_NAME"].strip(),
                    "latitude": float(row["LATITUDE"]),
                    "longitude": float(row["LONGITUDE"]),
                    "label": f"{city}, {state_code}",
                    "search_key": f"{normalize_city(city)} {state_code} {row['STATE_NAME'].upper()}",
                }
            )
    return tuple(records)


@lru_cache(maxsize=1)
def _load_city_lookup() -> dict[tuple[str, str], tuple[float, float]]:
    return {
        (normalize_city(record["city"]), record["state"]): (
            record["latitude"],
            record["longitude"],
        )
        for record in _load_city_records()
    }


def search_cities(query: str, limit: int = 8) -> list[dict]:
    query = query.strip()
    if len(query) < 2:
        return []

    parts = [part.strip() for part in query.split(",") if part.strip()]
    city_query = normalize_city(parts[0]) if parts else ""
    state_query = normalize_state(parts[1]) if len(parts) > 1 else ""

    matches: list[tuple[int, dict]] = []
    for record in _load_city_records():
        city_key = normalize_city(record["city"])
        if state_query and record["state"] != state_query:
            continue

        score = None
        if city_query:
            if city_key.startswith(city_query):
                score = 0
            elif city_query in city_key:
                score = 1
            elif city_query in record["search_key"]:
                score = 2
        elif query.upper() in record["search_key"]:
            score = 3

        if score is not None:
            matches.append((score, record))

    valid_states = set(STATE_NAME_TO_CODE.values())
    if state_query and state_query not in valid_states:
        return []

    matches.sort(key=lambda item: (item[0], item[1]["city"]))
    return [
        {
            "label": item[1]["label"],
            "city": item[1]["city"],
            "state": item[1]["state"],
            "state_name": item[1]["state_name"],
            "country": "USA",
            "latitude": item[1]["latitude"],
            "longitude": item[1]["longitude"],
        }
        for item in matches[:limit]
    ]


def city_state_to_coords(city: str, state: str) -> tuple[float, float] | None:
    return _load_city_lookup().get((normalize_city(city), state.strip().upper()))


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


@lru_cache(maxsize=512)
def geocode_us_location(query: str) -> tuple[float, float]:
    """Geocode a US address or place name via Nominatim (cached)."""
    geolocator = Nominatim(user_agent="fuel-route-api-assessment")
    location = geolocator.geocode(
        {"country": "USA", "city": query},
        timeout=10,
    )
    if location is None:
        location = geolocator.geocode(f"{query}, USA", timeout=10)
    if location is None:
        raise ValueError(f"Could not find a US location for: {query}")
    validate_usa_location(location.latitude, location.longitude, query)
    return location.latitude, location.longitude


STATE_NAME_TO_CODE = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC",
}


def normalize_state(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) == 2:
        return cleaned
    return STATE_NAME_TO_CODE.get(cleaned, cleaned)


def try_parse_coordinates(value: str) -> tuple[float, float] | None:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) < 2:
        return None
    try:
        lat = float(parts[0])
        lng = float(parts[1])
    except ValueError:
        return None
    if -90 <= lat <= 90 and -180 <= lng <= 180:
        return lat, lng
    return None


def try_parse_city_state(value: str) -> tuple[float, float] | None:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) < 2:
        return None
    city = parts[0]
    state = normalize_state(parts[1])
    return city_state_to_coords(city, state)


def parse_location(value: str) -> tuple[float, float]:
    """
    Accept any of:
    - Coordinates: 40.7128,-74.0060 (must be inside the USA)
    - City + state: New York, NY  or  Denver, Colorado
    - US place name: Chicago (uses Nominatim, USA only)
    """
    value = value.strip()
    if not value:
        raise ValueError("Location cannot be empty.")

    coords = try_parse_coordinates(value)
    if coords:
        validate_usa_location(coords[0], coords[1], value)
        return coords

    coords = try_parse_city_state(value)
    if coords:
        validate_usa_location(coords[0], coords[1], value)
        return coords

    coords = geocode_us_location(value)
    validate_usa_location(coords[0], coords[1], value)
    return coords


def meters_to_miles(meters: float) -> float:
    return meters * MILES_PER_METER
