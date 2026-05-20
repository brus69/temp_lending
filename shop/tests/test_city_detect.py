import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse

from shop.cities import (
    DEFAULT_CITY,
    get_client_ip,
    lookup_city_by_ip,
    match_city_name,
)


class CityMatchTests(TestCase):
    def test_match_russian_name(self):
        self.assertEqual(match_city_name("Нижний Новгород"), "Нижний Новгород")

    def test_match_english_alias(self):
        self.assertEqual(match_city_name("Saint Petersburg"), "Санкт-Петербург")

    def test_match_with_g_prefix(self):
        self.assertEqual(match_city_name("г. Казань"), "Казань")


class CityDetectApiTests(TestCase):
    def test_detect_city_endpoint_returns_json(self):
        request = RequestFactory().get("/api/city/detect/")
        request.META["REMOTE_ADDR"] = "8.8.8.8"
        from shop.views import detect_city

        with patch("shop.views.lookup_city_by_ip", return_value="Пермь"):
            response = detect_city(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["city"], "Пермь")

    def test_lookup_private_ip_returns_moscow(self):
        self.assertEqual(lookup_city_by_ip("127.0.0.1"), DEFAULT_CITY)

    def test_lookup_non_ru_country_returns_moscow(self):
        def fake_fetcher(ip: str):
            return {"status": "success", "countryCode": "US", "city": "New York", "regionName": ""}

        self.assertEqual(lookup_city_by_ip("1.2.3.4", fetcher=fake_fetcher), DEFAULT_CITY)

    def test_client_ip_from_forwarded_header(self):
        request = RequestFactory().get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 10.0.0.1"
        self.assertEqual(get_client_ip(request), "203.0.113.1")

    def test_detect_city_via_client(self):
        def fake_fetcher(ip: str):
            return {"status": "success", "countryCode": "RU", "city": "Самара", "regionName": ""}

        with patch("shop.cities._fetch_geo_ip_api", fake_fetcher):
            response = self.client.get(reverse("detect_city"), REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["city"], "Самара")
