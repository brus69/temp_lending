from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import CategorySpecAttribute, Product, ProductSpecValue, YandexFeedMode, YandexFeedParamRole
from shop.tests.factories import make_category, make_product


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class YandexFeedTests(TestCase):
    def setUp(self):
        self.category = make_category(name="Крепёж", slug="krepezh-feed")
        self.product = make_product(
            category=self.category,
            name="Болт М8",
            slug="bolt-m8-feed",
            sku="FEED-001",
            price=Decimal("150.00"),
            old_price=Decimal("200.00"),
            description="<p>Надёжный <b>болт</b></p>",
        )
        attr = CategorySpecAttribute.objects.create(
            category=self.category,
            name="Цвет",
            sort_order=1,
        )
        ProductSpecValue.objects.create(product=self.product, attribute=attr, value="чёрный")
        brand_attr = CategorySpecAttribute.objects.create(
            category=self.category,
            name="Бренд",
            sort_order=2,
            yandex_feed_param_role=YandexFeedParamRole.VENDOR,
        )
        ProductSpecValue.objects.create(product=self.product, attribute=brand_attr, value="FixPro")

    def test_feed_returns_yml_with_offer(self):
        response = self.client.get(reverse("yandex_market_feed"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/xml", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("<yml_catalog", body)
        self.assertIn('<offer id="FEED-001"', body)
        self.assertIn("<name>Болт М8</name>", body)
        self.assertIn("<price>150</price>", body)
        self.assertIn("<oldprice>200</oldprice>", body)
        self.assertIn(f'<categoryId>{self.category.pk}</categoryId>', body)
        self.assertIn('<param name="Цвет">чёрный</param>', body)
        self.assertIn("<vendor>FixPro</vendor>", body)
        self.assertIn("/product/bolt-m8-feed/", body)

    def test_feed_excludes_inactive_products(self):
        self.product.is_active = False
        self.product.redirect_product = make_product(
            category=self.category,
            name="Замена",
            slug="replacement-feed",
            sku="FEED-002",
            price=Decimal("50.00"),
        )
        self.product.save()
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertNotIn('id="FEED-001"', body)
        self.assertIn('id="FEED-002"', body)

    @override_settings(
        PUBLIC_SITE_URL="https://shop.example.com",
        YANDEX_FEED_CLID="12345",
    )
    def test_feed_uses_public_url_and_clid(self):
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertIn(
            "https://shop.example.com/product/bolt-m8-feed/?clid=12345",
            body,
        )
        self.assertIn("https://shop.example.com/", body)

    def test_feed_marks_unavailable_without_stock(self):
        Product.objects.filter(pk=self.product.pk).update(
            stock_store=0,
            stock_warehouse=0,
        )
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertIn('id="FEED-001" available="false"', body)

    def test_feed_respects_disabled_category(self):
        self.category.yandex_feed_enabled = False
        self.category.save(update_fields=["yandex_feed_enabled"])
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertNotIn('id="FEED-001"', body)

    def test_feed_product_can_override_disabled_category(self):
        self.category.yandex_feed_enabled = False
        self.category.save(update_fields=["yandex_feed_enabled"])
        self.product.yandex_feed_mode = YandexFeedMode.INCLUDE
        self.product.save(update_fields=["yandex_feed_mode"])
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertIn('id="FEED-001"', body)

    def test_feed_excludes_product_by_mode(self):
        self.product.yandex_feed_mode = YandexFeedMode.EXCLUDE
        self.product.save(update_fields=["yandex_feed_mode"])
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertNotIn('id="FEED-001"', body)

    def test_feed_excludes_spec_when_disabled_on_product(self):
        color_value = self.product.spec_values.get(attribute__name="Цвет")
        color_value.yandex_feed_include = False
        color_value.save(update_fields=["yandex_feed_include"])
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertNotIn('<param name="Цвет">', body)
        self.assertIn("<vendor>FixPro</vendor>", body)

    def test_feed_excludes_description_when_disabled(self):
        self.product.yandex_feed_include_description = False
        self.product.save(update_fields=["yandex_feed_include_description"])
        body = self.client.get(reverse("yandex_market_feed")).content.decode()
        self.assertNotIn("<description>", body)
