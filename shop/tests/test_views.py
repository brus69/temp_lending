from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from shop.models import Favorite, Manager, Order, OrderItem
from shop.tests.factories import make_category, make_product, make_user


class ShopFlowTests(TestCase):
    def setUp(self):
        self.category = make_category(name="Метизы", slug="metizy-test")
        self.product = make_product(
            category=self.category,
            name="Болт тестовый",
            slug="bolt-test",
            sku="SKU-T-001",
            price=Decimal("100.00"),
            old_price=Decimal("120.00"),
        )
        self.user = make_user(username="u1", email="u1@test.local", password="testpass123")
        self.manager = Manager.objects.create(
            name="Максим",
            phone="+7 (812) 507-64-54",
            is_active=True,
        )
        self.manager.categories.add(self.category)

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_product_detail_shows_expert_help_block(self, _seed_mock):
        response = self.client.get(reverse("product_detail", args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "vi-expert-help")
        self.assertContains(response, "Помощь эксперта")
        self.assertContains(response, "Заказать звонок")
        self.assertContains(response, "Максим")
        self.assertContains(response, "data-expert-request-open")
        self.assertContains(response, "Заявка на покупку товара")
        self.assertContains(response, "Оформить заказ")

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_expert_product_request_creates_order(self, _seed_mock):
        response = self.client.post(
            reverse("expert_product_request", args=[self.product.id]),
            {
                "customer_name": "Иван Иванович",
                "phone": "+79991234567",
                "manager_id": str(self.manager.id),
                "question": "Нужна консультация",
                "personal_data_consent": "1",
                "quantity": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.latest("id")
        self.assertEqual(order.customer_name, "Иван Иванович")
        self.assertIn("Менеджер: Максим", order.comment)
        self.assertIn("Нужна консультация", order.comment)
        self.assertEqual(order.items.get().quantity, 2)

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_sub_category_has_pagination(self, _seed_mock):
        for i in range(2, 27):
            make_product(
                category=self.category,
                name=f"Товар {i:02d}",
                slug=f"product-{i:02d}",
                sku=f"SKU-T-{i:03d}",
                price=Decimal("50.00"),
            )
        resp = self.client.get(reverse("sub_category_by_slug", args=[self.category.slug]))
        self.assertEqual(resp.status_code, 200)
        page_obj = resp.context["page_obj"]
        self.assertEqual(page_obj.paginator.num_pages, 3)
        self.assertEqual(len(page_obj.object_list), 12)
        self.assertTrue(resp.context["pagination_items"])

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_search_has_pagination_and_query_prefix(self, _seed_mock):
        for i in range(2, 19):
            make_product(
                category=self.category,
                name=f"Болт {i:02d}",
                slug=f"bolt-{i:02d}",
                sku=f"SKU-B-{i:03d}",
                price=Decimal("99.00"),
            )
        resp = self.client.get(reverse("search"), {"q": "Болт"})
        self.assertEqual(resp.status_code, 200)
        page_obj = resp.context["page_obj"]
        self.assertEqual(page_obj.paginator.count, 18)
        self.assertEqual(resp.context["pagination_prefix"], "q=%D0%91%D0%BE%D0%BB%D1%82&")

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_cart_checkout_creates_order_and_clears_cart(self, _seed_mock):
        add_url = reverse("cart_add", args=[self.product.id])
        self.client.post(add_url, {"quantity": 2, "next": reverse("cart")})
        checkout_url = reverse("checkout")
        resp = self.client.post(
            checkout_url,
            {
                "customer_name": "Иван",
                "phone": "+79990000000",
                "email": "buyer@test.local",
                "address": "ул. Тестовая, 1",
                "comment": "Позвоните перед доставкой",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.total_price, Decimal("200.00"))
        session = self.client.session
        self.assertEqual(session.get("cart", {}), {})

    @patch("shop.views._seed_demo_data", autospec=True)
    def test_favorite_toggle_for_logged_user(self, _seed_mock):
        self.client.login(username="u1", password="testpass123")
        url = reverse("favorite_toggle", args=[self.product.id])
        self.client.post(url, {"next": reverse("index")})
        self.assertTrue(Favorite.objects.filter(user=self.user, product=self.product).exists())
        self.client.post(url, {"next": reverse("index")})
        self.assertFalse(Favorite.objects.filter(user=self.user, product=self.product).exists())
