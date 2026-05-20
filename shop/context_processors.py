from django.conf import settings
from django.db.models import Prefetch

from .cart import cart_count
from .models import (
    Article,
    Category,
    CategorySpecAttribute,
    Favorite,
    News,
    ProductSpecValue,
    Promotion,
    TopMenuLink,
)


def cart_context(request):
    return {"cart_items_count": cart_count(request.session)}


def favorites_context(request):
    if request.user.is_authenticated:
        ids = frozenset(Favorite.objects.filter(user=request.user).values_list("product_id", flat=True))
        return {"favorite_product_ids": ids, "favorites_count": len(ids)}
    return {"favorite_product_ids": frozenset(), "favorites_count": 0}


def store_context(request):
    return {
        "store_name": settings.STORE_NAME,
    }


def header_menu_context(request):
    return {
        "header_menu_categories": Category.objects.filter(show_in_top_menu=True).order_by(
            "sort_order",
            "name",
        ),
    }


def header_top_menu_context(request):
    return {
        "header_top_links": TopMenuLink.objects.filter(is_active=True).order_by("sort_order", "id"),
    }


def catalog_menu_context(request):
    categories = list(
        Category.objects.order_by("sort_order", "name").prefetch_related(
            Prefetch(
                "spec_attributes",
                queryset=CategorySpecAttribute.objects.order_by("sort_order", "id"),
            ),
        ),
    )
    if not categories:
        return {"catalog_menu_categories": []}

    attr_ids = [attr.id for cat in categories for attr in cat.spec_attributes.all()]
    values_by_attr: dict[int, list[str]] = {attr_id: [] for attr_id in attr_ids}
    if attr_ids:
        for attr_id, value in (
            ProductSpecValue.objects.filter(attribute_id__in=attr_ids)
            .values_list("attribute_id", "value")
            .distinct()
            .order_by("attribute_id", "value")
        ):
            bucket = values_by_attr[attr_id]
            if len(bucket) < 6:
                bucket.append(value)

    menu_items = []
    for category in categories:
        attributes = [
            {
                "id": attribute.id,
                "name": attribute.name,
                "values": values_by_attr.get(attribute.id, []),
            }
            for attribute in category.spec_attributes.all()
        ]
        menu_items.append({"category": category, "attributes": attributes})
    return {"catalog_menu_categories": menu_items}


def footer_content_context(request):
    published = {"is_published": True}
    return {
        "footer_articles": Article.objects.filter(**published).order_by("-published_at", "-id")[:10],
        "footer_news": News.objects.filter(**published).order_by("-published_at", "-id")[:10],
        "footer_promotions": Promotion.objects.filter(**published).order_by("-published_at", "-id")[:10],
    }
