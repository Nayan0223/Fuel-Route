from unittest.mock import patch

from django.test import TestCase

from routing.models import FuelStation


class RouteApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        FuelStation.objects.create(
            opis_id=99,
            name="Test Station",
            address="Main St",
            city="Denver",
            state="CO",
            rack_id=1,
            retail_price=3.10,
            latitude=39.7392,
            longitude=-104.9903,
        )

    def test_missing_params_returns_400(self):
        response = self.client.get("/api/route/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    @patch("routing.views.fetch_route")
    @patch("routing.views.parse_location")
    def test_successful_route_response_shape(self, mock_parse, mock_route):
        mock_parse.side_effect = [(39.7392, -104.9903), (41.8781, -87.6298)]
        mock_route.return_value = {
            "geometry": {
                "type": "LineString",
                "coordinates": [[-104.99, 39.73], [-87.62, 41.87]],
            },
            "distance_miles": 600.0,
            "duration_seconds": 36000,
            "points": [(39.7392, -104.9903), (41.8781, -87.6298)],
        }

        response = self.client.get(
            "/api/route/?start=39.7392,-104.9903&finish=41.8781,-87.6298"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("route", payload)
        self.assertIn("fuel_stops", payload)
        self.assertIn("fuel_summary", payload)
        self.assertIn("map", payload)
        self.assertEqual(payload["map"]["type"], "FeatureCollection")
