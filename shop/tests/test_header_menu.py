from django.test import RequestFactory, TestCase

from shop.context_processors import catalog_menu_context, header_menu_context
from shop.tests.factories import make_category, make_product, make_product_spec_value, make_spec_attribute


class HeaderMenuTests(TestCase):
    def test_header_shows_categories_marked_for_top_menu(self):
        visible = make_category(name="Метизы", slug="metizy-menu", show_in_top_menu=True, sort_order=1)
        make_category(
            name="Скрытая",
            slug="hidden-menu",
            show_in_top_menu=False,
            is_featured=False,
            sort_order=2,
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        top_nav_start = content.find('overflow-x-auto px-4 py-2')
        self.assertGreater(top_nav_start, -1)
        top_nav_section = content[top_nav_start : top_nav_start + 2000]
        self.assertIn(visible.name, top_nav_section)
        self.assertNotIn("Скрытая", top_nav_section)

    def test_header_menu_order_by_sort_order(self):
        make_category(name="Б", slug="cat-b", show_in_top_menu=True, sort_order=2)
        make_category(name="А", slug="cat-a", show_in_top_menu=True, sort_order=1)

        categories = header_menu_context(RequestFactory().get("/"))["header_menu_categories"]
        self.assertEqual([category.name for category in categories], ["А", "Б"])


class CatalogMenuTests(TestCase):
    def test_catalog_menu_shows_all_categories_without_ozon_block(self):
        category = make_category(name="Метизы", slug="metizy-catalog", sort_order=1)
        make_category(name="Крепёж", slug="krepezh-catalog", sort_order=2)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Весь Ozon")
        self.assertContains(response, "Весь каталог")
        self.assertContains(response, category.name)
        self.assertContains(response, "data-catalog-category-trigger")

    def test_catalog_menu_includes_spec_values(self):
        category = make_category(name="Автокрепёж", slug="auto-catalog")
        attribute = make_spec_attribute(category=category, name="Диаметр", sort_order=1)
        make_product_spec_value(
            product=make_product(category=category),
            attribute=attribute,
            value="M6",
        )
        make_product_spec_value(
            product=make_product(category=category),
            attribute=attribute,
            value="M8",
        )

        items = catalog_menu_context(RequestFactory().get("/"))["catalog_menu_categories"]
        item = next(entry for entry in items if entry["category"].id == category.id)
        self.assertEqual(item["attributes"][0]["name"], "Диаметр")
        self.assertEqual(item["attributes"][0]["values"], ["M6", "M8"])
