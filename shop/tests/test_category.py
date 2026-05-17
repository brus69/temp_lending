from django.test import Client, TestCase, override_settings

from shop.models import Category, Product
from shop.views import _seed_demo_data, _sync_category_product_counts


class CategoryPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_category_page_shows_store_name(self):
        _seed_demo_data()
        response = self.client.get("/category/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Каталог товаров Все инструменты", content)
        self.assertNotIn("Подбор крепежа по DIN", content)

    @override_settings(STORE_NAME="Мой магазин")
    def test_category_page_uses_store_name_setting(self):
        _seed_demo_data()
        response = self.client.get("/category/")
        self.assertContains(response, "Каталог товаров Мой магазин")
        self.assertContains(response, "<h1", msg_prefix="один заголовок каталога")

    def test_category_page_shows_actual_product_counts(self):
        _seed_demo_data()
        _sync_category_product_counts()
        response = self.client.get("/category/")
        self.assertEqual(response.status_code, 200)
        metizy = Category.objects.get(slug="metizy")
        actual = Product.objects.filter(category=metizy).count()
        self.assertEqual(metizy.product_count, actual)
        self.assertIn(f"{actual} товаров", response.content.decode())
        self.assertNotIn("438150", response.content.decode())
