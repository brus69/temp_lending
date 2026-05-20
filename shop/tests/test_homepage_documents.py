from django.test import TestCase
from django.urls import reverse

from shop.models import HomepageDocument


class HomepageDocumentsTests(TestCase):
    def test_homepage_shows_certificate_and_thank_you_sections(self):
        HomepageDocument.objects.all().delete()
        HomepageDocument.objects.create(
            kind=HomepageDocument.Kind.CERTIFICATE,
            title="Сертификат ISO",
            image_url="https://example.com/cert.jpg",
            sort_order=0,
        )
        HomepageDocument.objects.create(
            kind=HomepageDocument.Kind.THANK_YOU,
            title="Письмо партнёру",
            image_url="https://example.com/thanks.jpg",
            sort_order=0,
        )

        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сертификаты")
        self.assertContains(response, "Благодарственные письма")
        self.assertContains(response, "vi-documents-carousel")
        self.assertContains(response, "Сертификат ISO")
        self.assertContains(response, "Письмо партнёру")

    def test_inactive_documents_are_hidden(self):
        HomepageDocument.objects.all().delete()
        HomepageDocument.objects.create(
            kind=HomepageDocument.Kind.CERTIFICATE,
            title="Скрытый",
            image_url="https://example.com/hidden.jpg",
            is_active=False,
        )

        response = self.client.get(reverse("index"))
        self.assertNotContains(response, "Скрытый")
