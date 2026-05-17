from django.test import Client, TestCase

from shop.models import Product
from shop.views import _seed_demo_data


class SubCategoryFiltersTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_sub_category_shows_spec_filters_for_category(self):
        _seed_demo_data()
        response = self.client.get("/sub-category/metizy/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Фильтры", content)
        self.assertIn("Цена, ₽", content)
        self.assertIn("DIN", content)
        self.assertIn("Диаметр резьбы", content)

    def test_sub_category_filters_products_by_spec(self):
        _seed_demo_data()
        response = self.client.get("/sub-category/metizy/", {"spec": []})
        all_count = len(response.context["page_obj"])

        din_attr_id = None
        for spec_filter in response.context["spec_filters"]:
            if spec_filter["attribute"].name == "DIN":
                din_attr_id = spec_filter["attribute"].id
                break
        self.assertIsNotNone(din_attr_id)

        filtered = self.client.get(
            "/sub-category/metizy/",
            {f"spec_{din_attr_id}": "9021"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertLess(len(filtered.context["page_obj"]), all_count)
        for product in filtered.context["page_obj"]:
            self.assertTrue(
                Product.objects.filter(
                    pk=product.pk,
                    spec_values__attribute_id=din_attr_id,
                    spec_values__value="9021",
                ).exists()
            )

    def test_furnitura_page_has_filters_block(self):
        _seed_demo_data()
        response = self.client.get("/sub-category/furnitura/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Фильтры")
        self.assertContains(response, "Скобяные изделия и фурнитура")
        self.assertRegex(response.content.decode(), r"Показать \d+ товар")

    def test_filter_count_api_returns_label(self):
        _seed_demo_data()
        response = self.client.get("/sub-category/auto-krepezh/filter-count/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 20)
        self.assertEqual(data["label"], "Показать 20 товаров")

        din_attr_id = next(
            f["attribute"].id
            for f in self.client.get("/sub-category/auto-krepezh/").context["spec_filters"]
            if f["attribute"].name == "Диаметр резьбы"
        )
        filtered = self.client.get(
            f"/sub-category/auto-krepezh/filter-count/",
            {f"spec_{din_attr_id}": "M14"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertLess(filtered.json()["count"], 20)
        self.assertIn("Показать", filtered.json()["label"])

    def test_filter_submit_button_shows_filtered_count(self):
        _seed_demo_data()
        response = self.client.get("/sub-category/auto-krepezh/")
        self.assertContains(response, "Показать 20 товаров")

        din_attr_id = next(
            f["attribute"].id
            for f in response.context["spec_filters"]
            if f["attribute"].name == "Диаметр резьбы"
        )
        filtered = self.client.get(
            "/sub-category/auto-krepezh/",
            {f"spec_{din_attr_id}": "M14"},
        )
        count = filtered.context["filtered_products_count"]
        self.assertIn(f"Показать {count}", filtered.content.decode())

    def test_auto_krepezh_has_twenty_products_and_thread_diameters(self):
        _seed_demo_data()
        from shop.models import Category

        category = Category.objects.get(slug="auto-krepezh")
        self.assertEqual(category.products.count(), 20)

        response = self.client.get("/sub-category/auto-krepezh/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Диаметр резьбы", content)
        for diameter in ("M10", "M12", "M13", "M14"):
            self.assertIn(diameter, content)

        spec_filter = next(
            (f for f in response.context["spec_filters"] if f["attribute"].name == "Диаметр резьбы"),
            None,
        )
        self.assertIsNotNone(spec_filter)
        filter_values = {opt["value"] for opt in spec_filter["values"]}
        self.assertIn("M10", filter_values)
        self.assertIn("M14", filter_values)
        self.assertGreaterEqual(len(filter_values), 8)
