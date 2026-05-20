from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import Article
from shop.tests.factories import make_category, make_product


class SitemapTests(TestCase):
    def setUp(self):
        self.category = make_category(name="Метизы", slug="metizy-sitemap")
        self.product = make_product(
            category=self.category,
            name="Болт",
            slug="bolt-sitemap",
            sku="SKU-SM-001",
            price=Decimal("100.00"),
        )

    def test_sitemap_returns_xml_with_public_urls(self):
        Article.objects.create(
            title="Тестовая статья",
            slug="test-article",
            body="Текст",
            is_published=True,
        )
        response = self.client.get(reverse("sitemap"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("/product/bolt-sitemap/", body)
        self.assertIn("/sub-category/metizy-sitemap/", body)
        self.assertIn("/articles/test-article/", body)
        self.assertNotIn("/cart/", body)
        self.assertNotIn("/account/", body)

    def test_sitemap_excludes_inactive_products(self):
        self.product.is_active = False
        self.product.redirect_product = make_product(
            category=self.category,
            name="Замена",
            slug="replacement-sitemap",
            sku="SKU-SM-002",
            price=Decimal("50.00"),
        )
        self.product.save()
        body = self.client.get(reverse("sitemap")).content.decode()
        self.assertNotIn("/product/bolt-sitemap/", body)
        self.assertIn("/product/replacement-sitemap/", body)

    @override_settings(PUBLIC_SITE_URL="https://shop.example.com")
    def test_sitemap_uses_public_site_url(self):
        body = self.client.get(reverse("sitemap")).content.decode()
        self.assertIn("https://shop.example.com/product/bolt-sitemap/", body)
