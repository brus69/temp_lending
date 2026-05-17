from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=False)
class NotFoundPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_custom_404_page(self):
        response = self.client.get("/nonexistent-page-xyz/")
        self.assertEqual(response.status_code, 404)
        content = response.content.decode()
        self.assertIn("404", content)
        self.assertIn("Страница не найдена", content)
        self.assertIn(reverse("index"), content)
