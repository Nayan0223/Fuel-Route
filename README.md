# Fuel Route API

Django REST API that plans US driving routes, finds cost-effective fuel stops, and calculates total fuel spend for a vehicle with a **500-mile range** and **10 MPG**.

## Project structure

```
fuel_p/
├── config/                 # Django project settings
├── routing/
│   ├── services/             # Business logic (routing, fuel, geocoding)
│   ├── templates/routing/
│   │   └── route_map.html  # Web map UI
│   ├── tests/                # Automated tests
│   ├── views.py              # API + map views
│   └── management/commands/
│       └── import_fuel_stations.py
├── data/us_cities.csv        # US city coordinates
├── fuel-prices-for-be-assessment.csv
├── postman/                  # Postman collection
└── requirements.txt
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_fuel_stations
python manage.py runserver
```

Open the web UI at `http://127.0.0.1:8000/`

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Interactive route map (web UI) |
| `GET /api/route/?start=...&finish=...` | Route, fuel stops, and cost |
| `GET /api/cities/?q=...` | USA city autocomplete search |

### Route example

```
GET /api/route/?start=40.7128,-74.0060&finish=34.0522,-118.2437
```

City names are also supported:

```
GET /api/route/?start=New York, NY&finish=Los Angeles, CA
```

### Response includes

- GeoJSON route geometry
- `map` FeatureCollection with route, start/finish, and fuel stop markers
- Optimal fuel stops every ~500 miles (cheapest nearby station)
- Total gallons consumed, gallons purchased, and total fuel cost

Import `postman/Fuel-Route-API.postman_collection.json` for ready-made requests.

## External services

| Service | Purpose | Calls per request |
|---------|---------|-------------------|
| [OSRM](https://project-osrm.org/) | Driving route + map geometry | 1 |
| [Nominatim](https://nominatim.org/) | Geocode place names (optional) | 0–2 |

Use `lat,lng` coordinates for start/finish to minimize external API calls.

## Assumptions

- Locations must be within the United States
- Vehicle starts with a full tank (first 500 miles need no purchase)
- Refuel when range would be exhausted (~every 500 miles)
- Fuel purchased at the cheapest station within 35 miles of the route

## Tests

```bash
python manage.py test routing
```

## Demo video checklist (Loom / Postman)

1. Run the server and open `http://127.0.0.1:8000/`
2. Search USA cities, load a route, show fuel stops on the map
3. Call `GET /api/route/` in Postman and walk through the JSON response
4. Briefly show `routing/views.py`, `routing/services/osrm.py`, and `routing/services/fuel.py`
