from django.test import TestCase

from shop.tests.factories import make_category, make_product


class ProductActiveTests(TestCase):
    def test_inactive_product_redirects_with_301(self):
        category = make_category()
        target = make_product(category=category, name="Активный", slug="active-product")
        inactive = make_product(
            category=category,
            name="Старый",
            slug="old-product",
            is_active=False,
            redirect_product=target,
        )
        response = self.client.get(f"/product/{inactive.slug}/")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], f"/product/{target.slug}/")

    def test_inactive_product_without_redirect_returns_404(self):
        product = make_product(is_active=False, redirect_product=None)
        response = self.client.get(f"/product/{product.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_inactive_product_hidden_from_category(self):
        category = make_category(slug="cat-active-test")
        active = make_product(category=category, slug="visible-product")
        make_product(category=category, slug="hidden-product", is_active=False)
        response = self.client.get("/sub-category/cat-active-test/")
        self.assertEqual(response.status_code, 200)
        slugs = [p.slug for p in response.context["page_obj"]]
        self.assertIn(active.slug, slugs)
        self.assertNotIn("hidden-product", slugs)
