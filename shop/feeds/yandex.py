from __future__ import annotations

import re
from decimal import Decimal
from xml.etree import ElementTree as ET

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from shop.models import (
    Category,
    Product,
    YandexFeedParamRole,
    product_specs_prefetch,
)
from shop.site_url import build_absolute_url, get_public_base_url


def _format_feed_price(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral_value():
        return str(int(quantized))
    return f"{quantized:.2f}"


def _plain_description(text: str, max_len: int = 3000) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_len:
        return f"{cleaned[: max_len - 3]}..."
    return cleaned


def _append_text(parent: ET.Element, tag: str, value: str) -> None:
    if not value:
        return
    child = ET.SubElement(parent, tag)
    child.text = value


def _append_params(offer_el: ET.Element, spec_values) -> str | None:
    """Возвращает vendor из характеристик, если найден."""
    vendor = None
    for spec in spec_values:
        if not spec.include_in_yandex_feed():
            continue
        name = (spec.attribute.name or "").strip()
        value = (spec.value or "").strip()
        if not name or not value:
            continue
        role = spec.attribute.yandex_feed_param_role
        if role == YandexFeedParamRole.VENDOR:
            vendor = vendor or value
            continue
        if role == YandexFeedParamRole.BARCODE:
            _append_text(offer_el, "barcode", value)
            continue
        param_el = ET.SubElement(offer_el, "param", name=name)
        param_el.text = value
    return vendor


def _product_available(product: Product) -> bool:
    return product.stock_store + product.stock_warehouse > 0


def _product_url(base_url: str, product: Product) -> str:
    path = reverse("product_detail", args=[product.slug])
    url = f"{base_url}{path}"
    clid = getattr(settings, "YANDEX_FEED_CLID", "").strip()
    if clid:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}clid={clid}"
    return url


def build_yandex_yml_feed(request=None) -> str:
    base_url = get_public_base_url(request)
    shop_url = f"{base_url}/"
    store_name = getattr(settings, "STORE_NAME", "Магазин")

    active_products = list(
        Product.objects.for_yandex_feed()
        .select_related("category")
        .prefetch_related(product_specs_prefetch())
        .order_by("pk"),
    )

    category_ids = {product.category_id for product in active_products}
    categories = Category.objects.filter(pk__in=category_ids).order_by("sort_order", "name")

    catalog_date = timezone.localtime().strftime("%Y-%m-%d %H:%M")
    root = ET.Element("yml_catalog", date=catalog_date)
    shop_el = ET.SubElement(root, "shop")

    _append_text(shop_el, "name", store_name)
    _append_text(shop_el, "company", store_name)
    _append_text(shop_el, "url", shop_url)

    currencies_el = ET.SubElement(shop_el, "currencies")
    ET.SubElement(currencies_el, "currency", id="RUB", rate="1")

    categories_el = ET.SubElement(shop_el, "categories")
    for category in categories:
        ET.SubElement(categories_el, "category", id=str(category.pk)).text = category.name

    offers_el = ET.SubElement(shop_el, "offers")

    for product in active_products:
        picture = build_absolute_url(product.primary_image_url, request)
        if not picture:
            continue

        offer_el = ET.SubElement(
            offers_el,
            "offer",
            id=product.sku,
            available="true" if _product_available(product) else "false",
        )

        _append_text(offer_el, "name", product.name)
        _append_text(offer_el, "price", _format_feed_price(product.price))
        _append_text(offer_el, "currencyId", "RUB")
        _append_text(offer_el, "categoryId", str(product.category_id))
        _append_text(offer_el, "picture", picture)
        _append_text(offer_el, "url", _product_url(base_url, product))
        _append_text(offer_el, "group_id", str(product.pk))

        vendor = _append_params(offer_el, product.spec_values.all())
        if vendor:
            _append_text(offer_el, "vendor", vendor)

        if product.has_discount and product.old_price:
            _append_text(offer_el, "oldprice", _format_feed_price(product.old_price))

        if product.yandex_feed_include_description:
            description = _plain_description(product.description)
            if description:
                _append_text(offer_el, "description", description)

    xml_body = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'
