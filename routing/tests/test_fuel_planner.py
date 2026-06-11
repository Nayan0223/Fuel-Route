from django.test import TestCase

from routing.models import FuelStation
from routing.services.fuel import build_route_profile, plan_fuel_stops


class FuelPlannerTests(TestCase):
    def setUp(self):
        self.stations = [
            FuelStation(
                opis_id=1,
                name="Cheap Stop",
                address="I-80",
                city="Omaha",
                state="NE",
                rack_id=1,
                retail_price=2.50,
                latitude=41.25,
                longitude=-95.93,
            ),
            FuelStation(
                opis_id=2,
                name="Expensive Stop",
                address="I-80",
                city="Des Moines",
                state="IA",
                rack_id=2,
                retail_price=4.00,
                latitude=41.60,
                longitude=-93.60,
            ),
        ]

    def test_short_trip_uses_cheapest_station_for_cost(self):
        profile = build_route_profile(
            [(41.25, -95.93), (41.60, -93.60)],
            total_distance_miles=300,
        )
        stops, summary = plan_fuel_stops(profile, 300, self.stations)

        self.assertEqual(len(stops), 0)
        self.assertEqual(summary["total_gallons_consumed"], 30.0)
        self.assertEqual(summary["total_cost_usd"], 75.0)

    def test_long_trip_creates_refuel_stops(self):
        points = [
            (41.25, -95.93),
            (41.40, -94.80),
            (41.60, -93.60),
            (41.60, -93.60),
        ]
        profile = build_route_profile(points, total_distance_miles=1200)
        stops, summary = plan_fuel_stops(profile, 1200, self.stations)

        self.assertEqual(len(stops), 2)
        self.assertEqual(stops[0].route_mile, 500)
        self.assertEqual(stops[1].route_mile, 1000)
        self.assertGreater(summary["gallons_purchased"], 0)
        self.assertGreater(summary["total_cost_usd"], 0)
