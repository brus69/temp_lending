from django.test import TestCase

from shop.models import ProductLabel
from shop.tests.factories import make_product, make_product_label


class ProductLabelTests(TestCase):
    def test_label_slug_autofill(self):
        label = ProductLabel.objects.create(name="Акция недели")
        self.assertTrue(label.slug)

    def test_product_displays_assigned_labels(self):
        label = make_product_label(name="Тестовая метка", slug="test-badge", background_class="bg-emerald-600")
        product = make_product()
        product.labels.add(label)
        response = self.client.get(f"/product/{product.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тестовая метка")
