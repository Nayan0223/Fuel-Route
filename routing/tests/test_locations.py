from django.test import TestCase

from routing.services.geo import (
    is_within_usa,
    parse_location,
    search_cities,
    try_parse_city_state,
    try_parse_coordinates,
    validate_usa_location,
)


class LocationParsingTests(TestCase):
    def test_coordinates_are_parsed(self):
        lat, lng = parse_location("40.7128,-74.0060")
        self.assertAlmostEqual(lat, 40.7128)
        self.assertAlmostEqual(lng, -74.0060)

    def test_city_state_is_parsed_from_local_data(self):
        lat, lng = parse_location("New York, NY")
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lng)

    def test_city_with_full_state_name(self):
        coords = try_parse_city_state("Denver, Colorado")
        self.assertIsNotNone(coords)

    def test_coordinates_helper_rejects_city_names(self):
        self.assertIsNone(try_parse_coordinates("New York, NY"))

    def test_city_search_returns_matches(self):
        results = search_cities("New York")
        self.assertGreater(len(results), 0)
        self.assertIn("NY", results[0]["state"])

    def test_city_search_api(self):
        response = self.client.get("/api/cities/?q=Denver")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["country"], "USA")
        self.assertGreater(len(payload["results"]), 0)
        self.assertEqual(payload["results"][0]["city"], "Denver")
        self.assertEqual(payload["results"][0]["country"], "USA")

    def test_non_us_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_location("48.8566,2.3522")

    def test_foreign_state_filter_returns_empty(self):
        self.assertEqual(search_cities("Paris, FR"), [])

    def test_usa_bounds_helper(self):
        self.assertTrue(is_within_usa(40.7128, -74.0060))
        self.assertFalse(is_within_usa(48.8566, 2.3522))
        with self.assertRaises(ValueError):
            validate_usa_location(51.5074, -0.1278, "London")
