from __future__ import annotations

from decimal import Decimal
from itertools import count

from django.contrib.auth import get_user_model

from shop.models import Category, CategorySpecAttribute, Product, ProductSpecValue


User = get_user_model()

_SEQ = count(1)


def _next_idx() -> int:
    return next(_SEQ)


def make_user(**overrides):
    idx = _next_idx()
    defaults = {
        "username": f"user_{idx}",
        "email": f"user_{idx}@test.local",
        "password": "testpass123",
    }
    defaults.update(overrides)
    password = defaults.pop("password")
    user = User.objects.create_user(**defaults)
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def make_category(**overrides):
    idx = _next_idx()
    defaults = {
        "name": f"Категория {idx}",
        "slug": f"category-{idx}",
        "image_url": "https://example.com/cat.png",
    }
    defaults.update(overrides)
    return Category.objects.create(**defaults)


def make_product(*, category: Category | None = None, **overrides):
    idx = _next_idx()
    category = category or make_category()
    defaults = {
        "category": category,
        "name": f"Товар {idx}",
        "slug": f"product-{idx}",
        "sku": f"SKU-T-{idx:05d}",
        "price": Decimal("100.00"),
        "old_price": Decimal("120.00"),
        "image_url": "https://example.com/product.png",
        "description": "Описание товара",
        "stock_store": 5,
        "stock_warehouse": 10,
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


def make_spec_attribute(*, category: Category, **overrides):
    idx = _next_idx()
    defaults = {
        "category": category,
        "name": f"Характеристика {idx}",
        "sort_order": idx,
    }
    defaults.update(overrides)
    return CategorySpecAttribute.objects.create(**defaults)


def make_product_spec_value(*, product: Product, attribute: CategorySpecAttribute, value: str = "test"):
    return ProductSpecValue.objects.create(product=product, attribute=attribute, value=value)
