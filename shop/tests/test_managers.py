from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from shop.managers_service import get_managers_for_category, get_primary_manager_for_category
from shop.models import Manager
from shop.tests.factories import make_category, make_product


class ManagerCategoryTests(TestCase):
    def setUp(self):
        Manager.objects.all().delete()
        self.category_a = make_category(name="Категория A", slug="cat-a")
        self.category_b = make_category(name="Категория B", slug="cat-b")
        self.category_empty = make_category(name="Без менеджеров", slug="cat-empty")
        self.manager_a = Manager.objects.create(name="Анна", phone="+7 111", is_active=True, sort_order=1)
        self.manager_b = Manager.objects.create(name="Борис", phone="+7 222", is_active=True, sort_order=2)
        self.manager_a.categories.add(self.category_a)
        self.manager_b.categories.add(self.category_b)

    def test_returns_managers_linked_to_category(self):
        managers = list(get_managers_for_category(self.category_a))
        self.assertEqual([m.name for m in managers], ["Анна"])

    def test_primary_manager_is_first_by_sort_order(self):
        primary = get_primary_manager_for_category(self.category_a)
        self.assertEqual(primary.name, "Анна")

    def test_category_without_managers_uses_any_active_fallback(self):
        managers = list(get_managers_for_category(self.category_empty))
        self.assertGreaterEqual(len(managers), 2)
        self.assertEqual(managers[0].name, "Анна")

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_product_page_uses_category_manager(self, _seed_mock):
        product = make_product(
            category=self.category_a,
            name="Товар",
            slug="tovar-a",
            sku="SKU-A",
            price=Decimal("10.00"),
        )
        response = self.client.get(reverse("product_detail", args=[product.slug]))
        self.assertContains(response, "Анна")
        self.assertNotContains(response, "Борис")
