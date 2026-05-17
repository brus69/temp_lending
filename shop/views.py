from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Count, Max, Min, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .cart import add_to_cart, build_cart_items, clear_cart, remove_from_cart, set_quantity
from .forms import ProductQuestionForm, ProductReviewForm, validate_review_image_files
from .models import (
    Category,
    Favorite,
    Order,
    OrderItem,
    Organization,
    Product,
    ProductGalleryImage,
    ProductQuestion,
    ProductReview,
    ProductReviewPhoto,
    ProductSpecValue,
    UserProfile,
    sync_product_specs_from_json,
)

EMAIL_CONFIRM_MAX_AGE_SECONDS = 60 * 60 * 24

PRODUCTS_PER_PAGE = 12


def _pagination_query_prefix(request, *, exclude: frozenset[str] = frozenset({"page"})) -> str:
    """Строка query-параметров для пагинации (без page)."""
    pairs: list[tuple[str, str]] = []
    for key in request.GET:
        if key in exclude:
            continue
        for value in request.GET.getlist(key):
            if value != "":
                pairs.append((key, value))
    if not pairs:
        return ""
    return urlencode(pairs) + "&"


def _parse_price_param(raw: str | None) -> Decimal | None:
    if not raw or not str(raw).strip():
        return None
    try:
        value = Decimal(str(raw).strip().replace(",", ".").replace(" ", ""))
    except Exception:
        return None
    if value < 0:
        return None
    return value


def _build_subcategory_filters(category: Category, request_get) -> tuple[list[dict], dict]:
    """Фильтры сайдбара для выбранной категории: цена и характеристики из БД."""
    base_qs = Product.objects.filter(category=category)
    bounds = base_qs.aggregate(min_price=Min("price"), max_price=Max("price"))

    price_filter = {
        "min_bound": bounds["min_price"],
        "max_bound": bounds["max_price"],
        "min_value": request_get.get("price_min", ""),
        "max_value": request_get.get("price_max", ""),
    }

    spec_filters: list[dict] = []
    attributes = category.spec_attributes.order_by("sort_order", "id")
    for attribute in attributes:
        value_rows = (
            ProductSpecValue.objects.filter(product__category=category, attribute=attribute)
            .values("value")
            .annotate(count=Count("id"))
            .order_by("value")
        )
        if not value_rows:
            continue
        selected = request_get.getlist(f"spec_{attribute.id}")
        spec_filters.append(
            {
                "attribute": attribute,
                "param": f"spec_{attribute.id}",
                "values": [
                    {
                        "value": row["value"],
                        "count": row["count"],
                        "selected": row["value"] in selected,
                    }
                    for row in value_rows
                ],
            }
        )

    return spec_filters, price_filter


def _apply_subcategory_filters(category: Category, request_get):
    """Возвращает queryset товаров с учётом GET-фильтров."""
    qs = Product.objects.filter(category=category).select_related("category")

    price_min = _parse_price_param(request_get.get("price_min"))
    price_max = _parse_price_param(request_get.get("price_max"))
    if price_min is not None:
        qs = qs.filter(price__gte=price_min)
    if price_max is not None:
        qs = qs.filter(price__lte=price_max)

    for attribute in category.spec_attributes.order_by("sort_order", "id"):
        selected = request_get.getlist(f"spec_{attribute.id}")
        if selected:
            qs = qs.filter(
                spec_values__attribute=attribute,
                spec_values__value__in=selected,
            ).distinct()

    return qs.order_by("name")


def _products_show_label(count: int) -> str:
    """Подпись кнопки фильтра: «Показать N товар(ов)»."""
    n = max(0, int(count))
    if n % 100 in (11, 12, 13, 14):
        suffix = "товаров"
    elif n % 10 == 1:
        suffix = "товар"
    elif n % 10 in (2, 3, 4):
        suffix = "товара"
    else:
        suffix = "товаров"
    return f"Показать {n} {suffix}"


def _pagination_nav_items(page_obj, *, on_each_side: int = 1, on_ends: int = 2) -> list[dict]:
    """Элементы для сегментированной пагинации (числа и пропуски)."""
    paginator = page_obj.paginator
    if paginator.num_pages <= 1:
        return []
    items: list[dict] = []
    for entry in paginator.get_elided_page_range(
        page_obj.number,
        on_each_side=on_each_side,
        on_ends=on_ends,
    ):
        if isinstance(entry, int):
            items.append({"kind": "page", "number": entry})
        else:
            items.append({"kind": "ellipsis"})
    return items


def _build_email_confirmation_token(user: User) -> str:
    signer = TimestampSigner(salt="shop-email-confirm")
    return signer.sign(f"{user.id}:{user.email}")


def _parse_email_confirmation_token(token: str) -> User | None:
    signer = TimestampSigner(salt="shop-email-confirm")
    try:
        raw = signer.unsign(token, max_age=EMAIL_CONFIRM_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    try:
        user_id_str, email = raw.split(":", 1)
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        return None
    return User.objects.filter(id=user_id, email__iexact=email).first()


def _send_confirmation_email(request, user: User) -> None:
    token = _build_email_confirmation_token(user)
    confirm_path = reverse("auth_confirm_email", args=[token])
    confirm_url = request.build_absolute_uri(confirm_path)
    send_mail(
        subject="Подтверждение email в LendingStore",
        message=(
            f"Здравствуйте!\n\n"
            f"Чтобы завершить регистрацию, подтвердите email по ссылке:\n{confirm_url}\n\n"
            f"Ссылка действует 24 часа."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


_AUTO_KREPEZH_IMAGE = (
    "https://images.unsplash.com/photo-1611835151646-5a9df7f11463?auto=format&fit=crop&w=900&q=80"
)


def _auto_krepezh_spec(
    diameter: str,
    *,
    pitch: str = "1.5",
    din: str = "967",
    material: str = "сталь 8.8",
    coating: str = "цинк",
    pack: str = "20 шт",
    key_size: str | None = None,
) -> dict:
    specs = {
        "Диаметр резьбы": diameter,
        "Шаг резьбы": pitch,
        "Направление резьбы": "правая",
        "Материал": material,
        "Покрытие": coating,
        "Фасовка": pack,
        "DIN": din,
    }
    if key_size:
        specs["Размер под ключ"] = key_size
    return specs


_AUTO_KREPEZH_SPECS: dict[str, dict] = {
    "klipsa-auto-uni-50": {
        "Диаметр резьбы": "M6",
        "Тип крепежа": "клипса",
        "Материал": "нейлон",
        "Покрытие": "—",
        "Фасовка": "50 шт",
        "Применение": "обшивка салона",
    },
    "vint-press-m5x16-50": _auto_krepezh_spec("M5", pitch="0.8", din="967", pack="50 шт", key_size="8 мм"),
    "auto-bolt-m6x16": _auto_krepezh_spec("M6", pitch="1.0", key_size="10 мм"),
    "auto-screw-trim-m8x18": _auto_krepezh_spec("M8", pitch="1.25", din="7985", pack="30 шт", key_size="13 мм"),
    "auto-bolt-m10x25": _auto_krepezh_spec("M10", pitch="1.25", key_size="17 мм"),
    "auto-bolt-m10x30-flan": _auto_krepezh_spec(
        "M10", pitch="1.25", din="6921", pack="10 шт", key_size="17 мм", coating="чёрный оксид"
    ),
    "auto-nut-m11x125": _auto_krepezh_spec("M11", pitch="1.25", din="934", pack="25 шт", key_size="17 мм"),
    "auto-nut-m12x125-wheel": _auto_krepezh_spec(
        "M12", pitch="1.25", din="7434", pack="4 шт", key_size="19 мм", material="сталь 10.9"
    ),
    "auto-stud-m12x15": _auto_krepezh_spec("M12", pitch="1.25", din="975", pack="2 шт", key_size="19 мм"),
    "auto-bolt-m13x35": _auto_krepezh_spec("M13", pitch="1.5", din="931", pack="15 шт", key_size="20 мм"),
    "auto-bolt-m14x40": _auto_krepezh_spec("M14", pitch="1.5", key_size="21 мм"),
    "auto-screw-m14x35-caliper": _auto_krepezh_spec(
        "M14", pitch="1.5", din="960", pack="8 шт", key_size="21 мм", coating="фосфат"
    ),
    "auto-nut-m14-flan": _auto_krepezh_spec("M14", pitch="1.5", din="6923", pack="12 шт", key_size="21 мм"),
    "auto-bolt-m16x45": _auto_krepezh_spec("M16", pitch="1.5", key_size="24 мм"),
    "auto-nut-m16-selflock": _auto_krepezh_spec(
        "M16", pitch="1.5", din="986", pack="10 шт", key_size="24 мм", coating="цинк жёлтый"
    ),
    "auto-stud-m18x15": _auto_krepezh_spec("M18", pitch="1.5", din="975", pack="2 шт", key_size="27 мм"),
    "auto-bolt-m20x50": _auto_krepezh_spec("M20", pitch="1.5", key_size="30 мм", material="сталь 10.9"),
    "auto-nut-m22x15": _auto_krepezh_spec("M22", pitch="1.5", din="934", pack="6 шт", key_size="32 мм"),
    "auto-bolt-m8x22": _auto_krepezh_spec("M8", pitch="1.25", pack="40 шт", key_size="13 мм"),
    "auto-washer-bolt-m10x28": _auto_krepezh_spec("M10", pitch="1.25", din="966", pack="15 шт", key_size="17 мм"),
}


def _demo_specs_dict_for_slug(slug: str) -> dict:
    """Демо-характеристики для товаров до синка в реляционную схему."""
    if slug in _AUTO_KREPEZH_SPECS:
        return _AUTO_KREPEZH_SPECS[slug]
    base = {
        "Шаг резьбы": "1.5",
        "Направление резьбы": "правая",
        "Материал": "сталь",
        "Покрытие": "цинк",
    }
    if slug == "shaiba-din9021-m8":
        return {
            **base,
            "Диаметр резьбы": "M8",
            "Размер под ключ": "13 мм",
            "Фасовка": "100 шт",
            "DIN": "9021",
        }
    if slug == "gaika-din934-m8":
        return {
            **base,
            "Диаметр резьбы": "M8",
            "Размер под ключ": "13 мм",
            "Фасовка": "100 шт",
            "DIN": "934",
        }
    if slug == "shpilka-din975":
        return {
            **base,
            "Диаметр резьбы": "M10",
            "Размер под ключ": "17 мм",
            "Фасовка": "1 шт",
            "DIN": "975",
        }
    return {
        **base,
        "Диаметр резьбы": "M10",
        "Размер под ключ": "17 мм",
        "Фасовка": "50 шт",
        "DIN": "934",
    }


# Демо-каталог: (category_slug, name, product_slug, sku, price, old_price, image_url)
_DEMO_PRODUCT_SEEDS: list[tuple[str, str, str, str, Decimal, Decimal | None, str]] = [
    (
        "metizy",
        "Гайка DIN934 оцинкованная M10 50 шт",
        "gaika-din934-m10",
        "SKU-015361",
        Decimal("210.00"),
        Decimal("358.00"),
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=1200&q=80",
    ),
    (
        "metizy",
        "Шайба DIN9021 кузовная M8 100 шт",
        "shaiba-din9021-m8",
        "SKU-015362",
        Decimal("270.00"),
        Decimal("377.00"),
        "https://images.unsplash.com/photo-1616789079464-9274d77b2d1f?auto=format&fit=crop&w=700&q=80",
    ),
    (
        "metizy",
        "Гайка DIN934 оцинкованная M8 100 шт",
        "gaika-din934-m8",
        "SKU-015363",
        Decimal("191.00"),
        Decimal("314.00"),
        "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=700&q=80",
    ),
    (
        "metizy",
        "Шпилька резьбовая DIN975",
        "shpilka-din975",
        "SKU-015364",
        Decimal("71.00"),
        Decimal("154.00"),
        "https://images.unsplash.com/photo-1609942072337-c3370e820d25?auto=format&fit=crop&w=700&q=80",
    ),
    (
        "metizy",
        "Болт DIN933 с полной резьбой M8×40 оцинк, 50 шт",
        "bolt-din933-m8x40-50",
        "SKU-DEMO-02001",
        Decimal("189.00"),
        Decimal("289.00"),
        "https://images.unsplash.com/photo-1567767326926-084838f5de88?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Болт DIN933 M10×50 оцинк, 25 шт",
        "bolt-din933-m10x50-25",
        "SKU-DEMO-02002",
        Decimal("245.00"),
        Decimal("349.00"),
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Винт ISO7380 с полукруглой головкой M6×16, 100 шт",
        "vint-iso7380-m6x16-100",
        "SKU-DEMO-02003",
        Decimal("312.00"),
        Decimal("445.00"),
        "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шайба плоская DIN125 M10, 200 шт",
        "shaiba-din125-m10-200",
        "SKU-DEMO-02004",
        Decimal("156.00"),
        Decimal("239.00"),
        "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Гайка самоконтрящаяся DIN985 M10, 50 шт",
        "gaika-din985-m10-50",
        "SKU-DEMO-02005",
        Decimal("228.00"),
        Decimal("340.00"),
        "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шайба пружинная DIN127 M8, 100 шт",
        "shaiba-din127-m8-100",
        "SKU-DEMO-02006",
        Decimal("134.00"),
        Decimal("210.00"),
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Винт самонарезающий по металлу 4.2×16, 500 шт",
        "vint-samorez-42x16-500",
        "SKU-DEMO-02007",
        Decimal("402.00"),
        Decimal("519.00"),
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Дюбель распорный 8×40, 50 шт",
        "dyubel-8x40-50",
        "SKU-DEMO-02008",
        Decimal("176.00"),
        Decimal("265.00"),
        "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Болт DIN933 с полной резьбой M6×20 оцинк, 100 шт",
        "bolt-din933-m6x20-100",
        "SKU-DEMO-02031",
        Decimal("148.00"),
        Decimal("219.00"),
        "https://images.unsplash.com/photo-1567767326926-084838f5de88?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Болт DIN931 с неполной резьбой M12×80 оцинк, 10 шт",
        "bolt-din931-m12x80-10",
        "SKU-DEMO-02032",
        Decimal("412.00"),
        Decimal("529.00"),
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Гайка шестигранная DIN934 M12 оцинк, 25 шт",
        "gaika-din934-m12-25",
        "SKU-DEMO-02033",
        Decimal("198.00"),
        Decimal("289.00"),
        "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шайба DIN9021 кузовная M12 оцинк, 50 шт",
        "shaiba-din9021-m12-50",
        "SKU-DEMO-02034",
        Decimal("224.00"),
        Decimal("335.00"),
        "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шплинт пружинный 3×40 мм, комплект 20 шт",
        "shplint-3x40-20",
        "SKU-DEMO-02035",
        Decimal("86.00"),
        Decimal("129.00"),
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шайба пружинная тяжёлая DIN127B M10, 100 шт",
        "shaiba-din127b-m10-100",
        "SKU-DEMO-02036",
        Decimal("162.00"),
        Decimal("239.00"),
        "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Винт ISO7380 с полукруглой головкой M8×20, нерж. А2, 50 шт",
        "vint-iso7380-m8x20-a2-50",
        "SKU-DEMO-02037",
        Decimal("498.00"),
        Decimal("649.00"),
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Винт DIN965 потайной M5×16 оцинк, 200 шт",
        "vint-din965-m5x16-200",
        "SKU-DEMO-02038",
        Decimal("274.00"),
        Decimal("359.00"),
        "https://images.unsplash.com/photo-1616789079464-9274d77b2d1f?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Гайка фланцевая с насечкой DIN6923 M10, 40 шт",
        "gaika-din6923-m10-40",
        "SKU-DEMO-02039",
        Decimal("356.00"),
        Decimal("459.00"),
        "https://images.unsplash.com/photo-1609942072337-c3370e820d25?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шпилька резьбовая DIN976-1 M16×500 (шт)",
        "shpilka-din976-m16x500",
        "SKU-DEMO-02040",
        Decimal("312.00"),
        Decimal("429.00"),
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Дюбель-гвоздь 6×60 мм для бетона, 100 шт",
        "dyubel-gvozd-6x60-100",
        "SKU-DEMO-02041",
        Decimal("388.00"),
        Decimal("499.00"),
        "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Забивной анкер для бетона M10×70 (комплект 10 шт)",
        "anker-zabivnoj-m10x70-10",
        "SKU-DEMO-02042",
        Decimal("560.00"),
        Decimal("719.00"),
        "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Болт профильный под Т-паз M10×25 (аль-профиль 45 мм)",
        "bolt-tpaz-m10x25-45",
        "SKU-DEMO-02043",
        Decimal("178.00"),
        Decimal("249.00"),
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Штифт цилиндрический DIN7 8×40 оцинк, 50 шт",
        "shtift-din7-8x40-50",
        "SKU-DEMO-02044",
        Decimal("204.00"),
        Decimal("299.00"),
        "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шпонка призматическая 8×7×40 мм DIN6888, 10 шт",
        "shponka-8x7x40-din6888-10",
        "SKU-DEMO-02045",
        Decimal("132.00"),
        Decimal("189.00"),
        "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Кольцо стопорное наружное 28 мм DIN471 (комплект 25 шт)",
        "kolco-stoporno-din471-28-25",
        "SKU-DEMO-02046",
        Decimal("168.00"),
        Decimal("235.00"),
        "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шуруп по дереву с потайной головкой 6×80 мм оцинк, 100 шт",
        "shurup-derevo-6x80-100",
        "SKU-DEMO-02047",
        Decimal("246.00"),
        Decimal("329.00"),
        "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Гайка барашковая M8 DIN315 оцинк, 50 шт",
        "gaika-barashkovaya-m8-50",
        "SKU-DEMO-02048",
        Decimal("218.00"),
        Decimal("299.00"),
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Гайка самостопорящаяся DIN986 оцинк M10, 50 шт",
        "gaika-din986-m10-50",
        "SKU-DEMO-02049",
        Decimal("238.00"),
        Decimal("319.00"),
        "https://images.unsplash.com/photo-1609942072337-c3370e820d25?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "metizy",
        "Шайба DIN9021 усиленная кузовная M16 оцинк, 25 шт",
        "shaiba-din9021-m16-25",
        "SKU-DEMO-02050",
        Decimal("296.00"),
        Decimal("405.00"),
        "https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "furnitura",
        "Петля накладная 100×75 мм, комплект 2 шт",
        "petlya-100x75-2",
        "SKU-DEMO-02009",
        Decimal("590.00"),
        Decimal("749.00"),
        "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "furnitura",
        "Ручка мебельная 128 мм, хром",
        "ruchka-128mm-hrom",
        "SKU-DEMO-02010",
        Decimal("340.00"),
        Decimal("459.00"),
        "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "furnitura",
        "Замок врезной 50 мм",
        "zamok-vreznoj-50",
        "SKU-DEMO-02011",
        Decimal("1120.00"),
        Decimal("1390.00"),
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "furnitura",
        "Уголок мебельный 30×30 мм, 4 шт",
        "ugolok-30x30-4",
        "SKU-DEMO-02012",
        Decimal("210.00"),
        Decimal("289.00"),
        "https://images.unsplash.com/photo-1615876234889-fd9cd39d6648?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "furnitura",
        "Ограничитель открывания двери",
        "ogranichitel-dveri-1",
        "SKU-DEMO-02013",
        Decimal("430.00"),
        Decimal("549.00"),
        "https://images.unsplash.com/photo-1584820927498-cfe5211fd8bf?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "special-krepezh",
        "Анкер клиновой M12×100",
        "anker-klin-m12x100",
        "SKU-DEMO-02014",
        Decimal("168.00"),
        Decimal("239.00"),
        "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "special-krepezh",
        "Анкер с болтом M10 L=80",
        "anker-bolt-m10-l80",
        "SKU-DEMO-02015",
        Decimal("142.00"),
        Decimal("205.00"),
        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "special-krepezh",
        "Дюбель с шурупом быстрый монтаж 10×80",
        "dyubel-bm-10x80",
        "SKU-DEMO-02016",
        Decimal("96.00"),
        Decimal("149.00"),
        "https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "special-krepezh",
        "Заклепка вытяжная 4×12, 50 шт",
        "zaklepka-vtyazhnaya-4x12",
        "SKU-DEMO-02017",
        Decimal("520.00"),
        Decimal("629.00"),
        "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "special-krepezh",
        "Хомут силовой одноболтовый 68–73 мм",
        "homut-silovoj-68",
        "SKU-DEMO-02018",
        Decimal("74.00"),
        Decimal("119.00"),
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "takelazh",
        "Трос стальной оцинкованный Ø4 мм, бухта 10 м",
        "tros-o4mm-10m",
        "SKU-DEMO-02019",
        Decimal("890.00"),
        Decimal("1049.00"),
        "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "takelazh",
        "Карабин монтажный 8 мм",
        "karabin-8mm",
        "SKU-DEMO-02020",
        Decimal("210.00"),
        Decimal("279.00"),
        "https://images.unsplash.com/photo-1590674899484-d5640e854abe?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "takelazh",
        "Цепь короткозвенная 6 мм, 5 м",
        "cep-6mm-5m",
        "SKU-DEMO-02021",
        Decimal("1540.00"),
        Decimal("1820.00"),
        "https://images.unsplash.com/photo-1589487391730-58fec20ad075?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "takelazh",
        "Строп текстильный петлевой 2 т / 2 м",
        "strop-2t-2m",
        "SKU-DEMO-02022",
        Decimal("680.00"),
        Decimal("849.00"),
        "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "plastic-krepezh",
        "Дюбель «ёлочка» 6×30, 100 шт",
        "dyubel-elochka-6x30",
        "SKU-DEMO-02023",
        Decimal("265.00"),
        Decimal("349.00"),
        "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "plastic-krepezh",
        "Клипса кабельная Ø12, 100 шт",
        "klipsa-kabel-12",
        "SKU-DEMO-02024",
        Decimal("198.00"),
        Decimal("269.00"),
        "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "plastic-krepezh",
        "Хомут нейлоновый 200×4.8 мм, 100 шт",
        "homut-nylon-200",
        "SKU-DEMO-02025",
        Decimal("412.00"),
        Decimal("519.00"),
        "https://images.unsplash.com/photo-1581092918056-0c4c3acd3789?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "auto-krepezh",
        "Клипса автомобильная универсальная, 50 шт",
        "klipsa-auto-uni-50",
        "SKU-DEMO-02026",
        Decimal("356.00"),
        Decimal("459.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Винт с прессшайбой M5×16 для пластика, 50 шт",
        "vint-press-m5x16-50",
        "SKU-DEMO-02027",
        Decimal("289.00"),
        Decimal("379.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт кузовной M6×16 DIN967, 20 шт",
        "auto-bolt-m6x16",
        "SKU-AUTO-001",
        Decimal("145.00"),
        Decimal("189.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Винт обшивки M8×18, 30 шт",
        "auto-screw-trim-m8x18",
        "SKU-AUTO-002",
        Decimal("178.00"),
        Decimal("229.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт кузовной M10×25 DIN967, 20 шт",
        "auto-bolt-m10x25",
        "SKU-AUTO-003",
        Decimal("212.00"),
        Decimal("279.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт с фланцем M10×30, 10 шт",
        "auto-bolt-m10x30-flan",
        "SKU-AUTO-004",
        Decimal("248.00"),
        Decimal("319.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Гайка M11×1.25, 25 шт",
        "auto-nut-m11x125",
        "SKU-AUTO-005",
        Decimal("265.00"),
        Decimal("339.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Гайка колёсная M12×1.25, 4 шт",
        "auto-nut-m12x125-wheel",
        "SKU-AUTO-006",
        Decimal("420.00"),
        Decimal("549.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Шпилька колесная M12×1.25×50, 2 шт",
        "auto-stud-m12x15",
        "SKU-AUTO-007",
        Decimal("385.00"),
        Decimal("489.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт крепления M13×1.5×35, 15 шт",
        "auto-bolt-m13x35",
        "SKU-AUTO-008",
        Decimal("298.00"),
        Decimal("379.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт M14×1.5×40, 12 шт",
        "auto-bolt-m14x40",
        "SKU-AUTO-009",
        Decimal("325.00"),
        Decimal("419.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Винт суппорта M14×1.5×35, 8 шт",
        "auto-screw-m14x35-caliper",
        "SKU-AUTO-010",
        Decimal("356.00"),
        Decimal("449.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Гайка фланцевая M14×1.5, 12 шт",
        "auto-nut-m14-flan",
        "SKU-AUTO-011",
        Decimal("312.00"),
        Decimal("399.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт M16×1.5×45, 10 шт",
        "auto-bolt-m16x45",
        "SKU-AUTO-012",
        Decimal("398.00"),
        Decimal("509.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Гайка самоконтрящаяся M16×1.5, 10 шт",
        "auto-nut-m16-selflock",
        "SKU-AUTO-013",
        Decimal("445.00"),
        Decimal("569.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Шпилька M18×1.5×60, 2 шт",
        "auto-stud-m18x15",
        "SKU-AUTO-014",
        Decimal("520.00"),
        Decimal("649.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт M20×1.5×50, 8 шт",
        "auto-bolt-m20x50",
        "SKU-AUTO-015",
        Decimal("585.00"),
        Decimal("729.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Гайка M22×1.5, 6 шт",
        "auto-nut-m22x15",
        "SKU-AUTO-016",
        Decimal("640.00"),
        Decimal("799.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт M8×1.25×22, 40 шт",
        "auto-bolt-m8x22",
        "SKU-AUTO-017",
        Decimal("165.00"),
        Decimal("215.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "auto-krepezh",
        "Болт с прессшайбой M10×28, 15 шт",
        "auto-washer-bolt-m10x28",
        "SKU-AUTO-018",
        Decimal("235.00"),
        Decimal("299.00"),
        _AUTO_KREPEZH_IMAGE,
    ),
    (
        "montazhnye-lenty",
        "Лента монтажная двусторонняя 25 мм × 5 м",
        "lenta-dvustoron-25",
        "SKU-DEMO-02028",
        Decimal("420.00"),
        Decimal("549.00"),
        "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "montazhnye-lenty",
        "Скотч алюминиевый 48 мм × 25 м",
        "skotch-al-48",
        "SKU-DEMO-02029",
        Decimal("980.00"),
        Decimal("1190.00"),
        "https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=900&q=80",
    ),
    (
        "chemical",
        "Химический анкер 300 мл (смола + отвердитель)",
        "himicheskiy-anker-300ml",
        "SKU-DEMO-02030",
        Decimal("2140.00"),
        Decimal("2590.00"),
        "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=900&q=80",
    ),
]


def _sync_category_product_counts() -> None:
    """Обновляет product_count по фактическому числу товаров в категории."""
    for category in Category.objects.annotate(actual_count=Count("products")):
        if category.product_count != category.actual_count:
            Category.objects.filter(pk=category.pk).update(product_count=category.actual_count)


def _sync_product_specs_from_dict(product: Product, specs: dict) -> None:
    """Приводит значения характеристик товара к заданному словарю (для демо-сидов)."""
    if not specs:
        return
    current = {
        sv.attribute.name: sv.value
        for sv in product.spec_values.select_related("attribute")
    }
    if current == specs:
        return
    product.spec_values.all().delete()
    product.specs = specs
    product.save(update_fields=["specs"])
    sync_product_specs_from_json(product)


def _ensure_demo_products() -> None:
    """Идемпотентно создаёт демо-товары по slug (включая расширенный каталог метизов)."""
    categories_by_slug = {c.slug: c for c in Category.objects.all()}
    if not categories_by_slug:
        return
    for idx, (cat_slug, name, slug, sku, price, old_price, image_url) in enumerate(_DEMO_PRODUCT_SEEDS):
        category = categories_by_slug.get(cat_slug)
        if not category:
            continue
        stock_base = 70 + (idx % 11) * 15
        obj, created = Product.objects.get_or_create(
            slug=slug,
            defaults={
                "category": category,
                "name": name,
                "sku": sku,
                "price": price,
                "old_price": old_price,
                "image_url": image_url,
                "description": "Демонстрационная позиция каталога для тестирования витрины и карточки товара.",
                "specs": _demo_specs_dict_for_slug(slug),
                "stock_store": stock_base,
                "stock_warehouse": stock_base + 120,
            },
        )
        if created:
            sync_product_specs_from_json(obj)
        elif not obj.spec_values.exists() and (obj.specs or {}):
            sync_product_specs_from_json(obj)
        elif cat_slug == "auto-krepezh" and slug in _AUTO_KREPEZH_SPECS:
            _sync_product_specs_from_dict(obj, _AUTO_KREPEZH_SPECS[slug])
    _sync_category_product_counts()


def _seed_reviews_questions_if_needed() -> None:
    """Тестовые отзывы и вопросы — один раз при пустой таблице отзывов."""
    if ProductReview.objects.exists():
        return
    products = list(Product.objects.order_by("id")[:4])
    if not products:
        return

    def ensure_demo_user(username: str, email: str, first_name: str = "") -> User:
        user, _created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "is_active": True,
            },
        )
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])
        if first_name and not user.first_name:
            user.first_name = first_name
            user.save(update_fields=["first_name"])
        if not user.has_usable_password():
            user.set_password("demo123")
            user.save()
        return user

    u1 = ensure_demo_user("demo_reviewer_1", "demo_reviewer_1@test.com", "Алексей")
    u2 = ensure_demo_user("demo_reviewer_2", "demo_reviewer_2@test.com", "Марина")

    p0 = products[0]
    r1 = ProductReview.objects.create(
        product=p0,
        user=u1,
        rating=5,
        text="Отличное качество резьбы, комплект полный. Заказываю не первый раз.",
    )
    ProductReview.objects.create(
        product=p0,
        user=u2,
        rating=4,
        text="Нормальные гайки, упаковка целая. Одну звезду сняла за цену без акции.",
    )

    try:
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (120, 120), color=(220, 230, 240)).save(buf, format="PNG")
        buf.seek(0)
        ProductReviewPhoto.objects.create(
            review=r1,
            image=ContentFile(buf.read(), name="demo_review_1.png"),
        )
        buf2 = BytesIO()
        Image.new("RGB", (100, 100), color=(180, 200, 180)).save(buf2, format="PNG")
        buf2.seek(0)
        ProductReviewPhoto.objects.create(
            review=r1,
            image=ContentFile(buf2.read(), name="demo_review_2.png"),
        )
    except Exception:
        pass

    if len(products) > 1:
        ProductReview.objects.create(
            product=products[1],
            user=u1,
            rating=5,
            text="Шайбы ровные, без заусенцев. Рекомендую.",
        )

    ProductQuestion.objects.create(
        product=p0,
        user=u2,
        text="Подойдёт ли для оцинкованного профиля на улице?",
        answer_text="Да, покрытие цинка рассчитано на открытое использование при типовых условиях.",
        answered_at=timezone.now(),
    )
    ProductQuestion.objects.create(
        product=p0,
        user=u1,
        text="Есть ли сертификат соответствия?",
    )

    for p in products:
        p.refresh_review_aggregate()


def _seed_demo_data() -> None:
    if not Category.objects.exists():
        categories_data = [
            ("Метизы", "metizy", "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=260&q=80"),
            ("Скобяные изделия и фурнитура", "furnitura", "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=260&q=80"),
            ("Специальный крепеж", "special-krepezh", "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=260&q=80"),
            ("Такелаж", "takelazh", "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=260&q=80"),
            ("Пластиковый крепеж", "plastic-krepezh", "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=260&q=80"),
            ("Автомобильный крепеж", "auto-krepezh", "https://images.unsplash.com/photo-1611835151646-5a9df7f11463?auto=format&fit=crop&w=260&q=80"),
            ("Монтажные ленты", "montazhnye-lenty", "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=260&q=80"),
            ("Химический", "chemical", "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=260&q=80"),
        ]
        for idx, (name, slug, image_url) in enumerate(categories_data, start=1):
            Category.objects.create(
                name=name,
                slug=slug,
                product_count=0,
                image_url=image_url,
                sort_order=idx,
            )

    _ensure_demo_products()
    _seed_reviews_questions_if_needed()


def index(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)[:6]
    promo_products = Product.objects.all()[:4]
    return render(request, "shop/index.html", {"categories": categories, "promo_products": promo_products})


def category(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    return render(request, "shop/category.html", {"categories": categories})


def sub_category_filter_count(request, slug):
    """JSON: количество товаров по текущим параметрам фильтра (для живого обновления кнопки)."""
    _seed_demo_data()
    category = get_object_or_404(Category, slug=slug)
    count = _apply_subcategory_filters(category, request.GET).count()
    return JsonResponse({"count": count, "label": _products_show_label(count)})


def sub_category(request, slug=None):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    current_category = Category.objects.filter(slug=slug).first() if slug else categories.first()
    spec_filters: list[dict] = []
    price_filter: dict = {}
    if current_category:
        spec_filters, price_filter = _build_subcategory_filters(current_category, request.GET)
        products_qs = _apply_subcategory_filters(current_category, request.GET)
    else:
        products_qs = Product.objects.none()
    page_obj = Paginator(products_qs, PRODUCTS_PER_PAGE).get_page(request.GET.get("page"))
    filtered_products_count = page_obj.paginator.count
    return render(
        request,
        "shop/sub_category.html",
        {
            "categories": categories,
            "current_category": current_category,
            "spec_filters": spec_filters,
            "price_filter": price_filter,
            "filtered_products_count": filtered_products_count,
            "filter_submit_label": _products_show_label(filtered_products_count),
            "page_obj": page_obj,
            "pagination_prefix": _pagination_query_prefix(request),
            "pagination_items": _pagination_nav_items(page_obj),
        },
    )


def product_detail(request, slug=None):
    _seed_demo_data()
    if not slug:
        first = Product.objects.first()
        if not first:
            return redirect("index")
        return redirect("product_detail", slug=first.slug)
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(
            Prefetch(
                "spec_values",
                queryset=ProductSpecValue.objects.select_related("attribute").order_by(
                    "attribute__sort_order",
                    "attribute__id",
                ),
            ),
            Prefetch(
                "gallery_images",
                queryset=ProductGalleryImage.objects.order_by("sort_order", "id"),
            ),
        ),
        slug=slug,
    )

    review_form = ProductReviewForm()
    question_form = ProductQuestionForm()
    redirect_anchor = reverse("product_detail", kwargs={"slug": product.slug})

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_review":
            if not request.user.is_authenticated:
                messages.warning(request, "Войдите в аккаунт, чтобы оставить отзыв.")
                return redirect(f"{redirect_anchor}#product-reviews")
            if ProductReview.objects.filter(user=request.user, product=product).exists():
                messages.error(request, "Вы уже оставили отзыв об этом товаре.")
                return redirect(f"{redirect_anchor}#product-reviews")

            review_form = ProductReviewForm(request.POST)
            files = request.FILES.getlist("images")
            try:
                validate_review_image_files(files)
            except ValidationError as exc:
                review_form.add_error(None, exc)

            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.user = request.user
                review.product = product
                review.save()
                for f in files:
                    ProductReviewPhoto.objects.create(review=review, image=f)
                product.refresh_review_aggregate()
                messages.success(request, "Спасибо, ваш отзыв опубликован.")
                return redirect(f"{redirect_anchor}#product-reviews")

            messages.error(request, "Проверьте данные в форме отзыва.")

        elif action == "add_question":
            if not request.user.is_authenticated:
                messages.warning(request, "Войдите в аккаунт, чтобы задать вопрос.")
                return redirect(f"{redirect_anchor}#product-questions")

            question_form = ProductQuestionForm(request.POST)
            if question_form.is_valid():
                q_obj = question_form.save(commit=False)
                q_obj.user = request.user
                q_obj.product = product
                q_obj.save()
                messages.success(request, "Вопрос отправлен. Ответ появится после проверки.")
                return redirect(f"{redirect_anchor}#product-questions")

            messages.error(request, "Проверьте текст вопроса.")

    reviews = product.reviews.select_related("user").prefetch_related("photos")
    questions = list(product.questions.select_related("user"))
    user_has_review = (
        request.user.is_authenticated
        and ProductReview.objects.filter(user=request.user, product=product).exists()
    )

    return render(
        request,
        "shop/product_detail.html",
        {
            "product": product,
            "reviews": reviews,
            "questions": questions,
            "review_form": review_form,
            "question_form": question_form,
            "user_has_review": user_has_review,
            "questions_count": len(questions),
        },
    )


@require_POST
def cart_add(request, product_id):
    _seed_demo_data()
    product = get_object_or_404(Product, id=product_id)
    qty = int(request.POST.get("quantity", 1))
    add_to_cart(request.session, product.id, qty)
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "cart"
    return redirect(next_url)


@require_POST
def cart_update(request, product_id):
    qty = int(request.POST.get("quantity", 1))
    set_quantity(request.session, product_id, qty)
    return redirect("cart")


@require_POST
def cart_remove(request, product_id):
    remove_from_cart(request.session, product_id)
    return redirect("cart")


@require_POST
def quick_order(request, product_id):
    _seed_demo_data()
    product = get_object_or_404(Product, id=product_id)
    try:
        qty = max(1, int(request.POST.get("quantity", 1) or 1))
    except (TypeError, ValueError):
        qty = 1
    customer_name = request.POST.get("customer_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    comment = request.POST.get("comment", "").strip()
    if not customer_name or not phone:
        return redirect("product_detail", slug=product.slug)
    order = Order.objects.create(
        customer_name=customer_name,
        phone=phone,
        address="(уточнить по телефону)",
        comment=comment,
        total_price=product.price * qty,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=qty,
        unit_price=product.price,
    )
    return redirect("checkout_success", order_id=order.id)


def cart_page(request):
    items, total = build_cart_items(request.session)
    return render(request, "shop/cart.html", {"cart_items": items, "cart_total": total})


def checkout(request):
    items, total = build_cart_items(request.session)
    if not items:
        return redirect("cart")

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()
        comment = request.POST.get("comment", "").strip()

        if customer_name and phone and address:
            order = Order.objects.create(
                customer_name=customer_name,
                phone=phone,
                email=email,
                address=address,
                comment=comment,
                total_price=total,
            )
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item["product"],
                        quantity=item["quantity"],
                        unit_price=item["product"].price,
                    )
                    for item in items
                ]
            )
            clear_cart(request.session)
            return redirect("checkout_success", order_id=order.id)

        return render(
            request,
            "shop/checkout.html",
            {
                "cart_items": items,
                "cart_total": total,
                "error": "Заполните обязательные поля: имя, телефон и адрес.",
            },
        )

    return render(request, "shop/checkout.html", {"cart_items": items, "cart_total": total})


def checkout_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/checkout_success.html", {"order": order})


def search(request):
    query = request.GET.get("q", "").strip()
    products_qs = Product.objects.none()
    if query:
        products_qs = (
            Product.objects.filter(
                Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query),
            )
            .select_related("category")
            .order_by("name")
        )
    page_obj = Paginator(products_qs, PRODUCTS_PER_PAGE).get_page(request.GET.get("page"))
    pagination_prefix = (urlencode({"q": query}) + "&") if query else ""
    return render(
        request,
        "shop/search.html",
        {
            "query": query,
            "page_obj": page_obj,
            "pagination_prefix": pagination_prefix,
            "pagination_items": _pagination_nav_items(page_obj),
        },
    )


def _orders_for_user(request):
    if request.user.is_authenticated and request.user.email:
        return Order.objects.filter(email__iexact=request.user.email).prefetch_related("items", "items__product")[:20]
    return Order.objects.prefetch_related("items", "items__product")[:20]


def _redirect_after_favorite(request):
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(reverse("index"))


@login_required(login_url=reverse_lazy("index"))
@require_POST
def favorite_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    fav = Favorite.objects.filter(user=request.user, product_id=product.id).first()
    if fav:
        fav.delete()
    else:
        Favorite.objects.get_or_create(user=request.user, product=product)
    return _redirect_after_favorite(request)


@login_required(login_url=reverse_lazy("index"))
def account_favorites(request):
    favorites = Favorite.objects.filter(user=request.user).select_related("product").order_by("-created_at")
    return render(request, "shop/account_favorites.html", {"favorites": favorites})


@login_required
def account(request):
    return render(request, "shop/account.html")


@login_required
def account_orders(request):
    orders = _orders_for_user(request)
    return render(request, "shop/account_orders.html", {"orders": orders})


def _personal_notice_message(request):
    key = (request.GET.get("notice") or "").strip()
    return {
        "profile_saved": "Личные данные сохранены.",
        "password_changed": "Пароль успешно изменён.",
    }.get(key, "")


@login_required
def account_personal_data(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(
        request,
        "shop/account_personal_data.html",
        {
            "profile": profile,
            "personal_success": _personal_notice_message(request),
        },
    )


@login_required
def account_personal_data_edit(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        delivery_address = (request.POST.get("delivery_address") or "").strip()[:2000]
        user.first_name = first_name[:150]
        user.last_name = last_name[:150]
        user.save(update_fields=["first_name", "last_name"])
        profile.phone = phone[:32]
        profile.delivery_address = delivery_address
        profile.save(update_fields=["phone", "delivery_address"])
        return redirect(f"{reverse('account_personal_data')}?notice=profile_saved")

    return render(
        request,
        "shop/account_personal_data_edit.html",
        {"profile": profile},
    )


@login_required
def account_password_change(request):
    user = request.user
    password_error = ""

    if request.method == "POST":
        old_password = request.POST.get("old_password") or ""
        new_password1 = request.POST.get("new_password1") or ""
        new_password2 = request.POST.get("new_password2") or ""
        if not user.check_password(old_password):
            password_error = "Неверный текущий пароль."
        elif len(new_password1) < 6:
            password_error = "Новый пароль должен быть не короче 6 символов."
        elif new_password1 != new_password2:
            password_error = "Новые пароли не совпадают."
        else:
            user.set_password(new_password1)
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)
            return redirect(f"{reverse('account_personal_data')}?notice=password_changed")

    return render(
        request,
        "shop/account_password_change.html",
        {"password_error": password_error},
    )


def _organization_form_from_post(post):
    return {
        "name": (post.get("name") or "").strip(),
        "inn": (post.get("inn") or "").strip(),
        "kpp": (post.get("kpp") or "").strip(),
        "legal_address": (post.get("legal_address") or "").strip(),
    }


def _validate_organization(owner, form_data, *, exclude_org=None):
    if not form_data["name"] or not form_data["inn"]:
        return "Заполните обязательные поля: название и ИНН."
    if not form_data["inn"].isdigit() or len(form_data["inn"]) not in (10, 12):
        return "ИНН должен содержать 10 или 12 цифр."
    if form_data["kpp"] and (not form_data["kpp"].isdigit() or len(form_data["kpp"]) != 9):
        return "КПП должен содержать 9 цифр."
    qs = Organization.objects.filter(owner=owner, inn=form_data["inn"])
    if exclude_org is not None:
        qs = qs.exclude(pk=exclude_org.pk)
    if qs.exists():
        return "Организация с таким ИНН уже добавлена."
    return None


def _notice_message(request):
    key = (request.GET.get("notice") or "").strip()
    messages_map = {
        "created": "Организация успешно добавлена.",
        "updated": "Изменения сохранены.",
        "deleted": "Организация удалена.",
    }
    return messages_map.get(key, "")


@login_required
def account_organizations(request):
    organizations = Organization.objects.filter(owner=request.user)
    notice_success = _notice_message(request)

    editing_org = None
    edit_pk = request.GET.get("edit")
    if edit_pk:
        try:
            editing_org = organizations.filter(pk=int(edit_pk)).first()
        except (TypeError, ValueError):
            editing_org = None

    empty_form = {"name": "", "inn": "", "kpp": "", "legal_address": ""}

    if editing_org:
        org_form = {
            "name": editing_org.name,
            "inn": editing_org.inn,
            "kpp": editing_org.kpp or "",
            "legal_address": editing_org.legal_address or "",
        }
    else:
        org_form = dict(empty_form)

    error = ""
    success = notice_success

    if request.method == "POST":
        action = (request.POST.get("action") or "create").strip()
        form_data = _organization_form_from_post(request.POST)

        if action == "delete":
            raw_id = request.POST.get("org_id")
            try:
                org = organizations.get(pk=int(raw_id))
            except (TypeError, ValueError, Organization.DoesNotExist):
                error = "Не удалось удалить организацию."
            else:
                org.delete()
                return redirect(f"{reverse('account_organizations')}?notice=deleted")

        elif action == "update":
            raw_id = request.POST.get("org_id")
            try:
                org = organizations.get(pk=int(raw_id))
            except (TypeError, ValueError, Organization.DoesNotExist):
                error = "Организация не найдена."
                org_form = form_data
                editing_org = None
            else:
                editing_org = org
                org_form = form_data
                err = _validate_organization(request.user, form_data, exclude_org=org)
                if err:
                    error = err
                else:
                    org.name = form_data["name"]
                    org.inn = form_data["inn"]
                    org.kpp = form_data["kpp"]
                    org.legal_address = form_data["legal_address"]
                    org.save()
                    return redirect(f"{reverse('account_organizations')}?notice=updated")

        else:
            org_form = form_data
            editing_org = None
            err = _validate_organization(request.user, form_data)
            if err:
                error = err
            else:
                Organization.objects.create(owner=request.user, **form_data)
                return redirect(f"{reverse('account_organizations')}?notice=created")

    show_edit_form = editing_org is not None
    show_create_form = editing_org is None and (
        request.GET.get("create") == "1"
        or (
            request.method == "POST"
            and (request.POST.get("action") or "create").strip() == "create"
            and error
        )
    )

    organizations = Organization.objects.filter(owner=request.user)

    return render(
        request,
        "shop/account_organizations.html",
        {
            "organizations": organizations,
            "org_form": org_form,
            "org_error": error,
            "org_success": success,
            "show_create_form": show_create_form,
            "show_edit_form": show_edit_form,
            "editing_org": editing_org,
        },
    )


@require_POST
def auth_email_check(request):
    email = (request.POST.get("email") or "").strip().lower()
    if not email:
        return JsonResponse({"ok": False, "error": "Введите email."}, status=400)
    exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({"ok": True, "exists": exists, "email": email})


@require_POST
def auth_login(request):
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    if not email or not password:
        return JsonResponse({"ok": False, "error": "Введите email и пароль."}, status=400)
    user = authenticate(request, username=email, password=password)
    if not user:
        return JsonResponse({"ok": False, "error": "Неверный email или пароль."}, status=400)
    if not user.is_active:
        return JsonResponse({"ok": False, "error": "Подтвердите email, затем выполните вход."}, status=400)
    login(request, user)
    return JsonResponse({"ok": True, "redirect_url": request.POST.get("next") or "/"})


@require_POST
def auth_register(request):
    email = (request.POST.get("email") or "").strip().lower()
    password1 = request.POST.get("password1") or ""
    password2 = request.POST.get("password2") or ""

    if not email:
        return JsonResponse({"ok": False, "error": "Введите email."}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({"ok": False, "error": "Пользователь с таким email уже существует."}, status=400)
    if len(password1) < 6:
        return JsonResponse({"ok": False, "error": "Пароль должен быть не короче 6 символов."}, status=400)
    if password1 != password2:
        return JsonResponse({"ok": False, "error": "Пароли не совпадают."}, status=400)

    user = User.objects.create_user(username=email, email=email, password=password1, is_active=False)
    try:
        _send_confirmation_email(request, user)
    except Exception:
        user.delete()
        return JsonResponse(
            {"ok": False, "error": "Не удалось отправить письмо подтверждения. Попробуйте позже."},
            status=500,
        )
    return JsonResponse({"ok": True, "email": email})


@require_POST
def auth_logout(request):
    logout(request)
    return redirect(request.POST.get("next") or "index")


def auth_confirm_email(request, token):
    user = _parse_email_confirmation_token(token)
    if not user:
        return render(
            request,
            "shop/auth_confirm_email_result.html",
            {"success": False, "title": "Ссылка недействительна", "message": "Проверьте ссылку или запросите регистрацию заново."},
        )
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    login(request, user)
    return render(
        request,
        "shop/auth_confirm_email_result.html",
        {"success": True, "title": "Email подтвержден", "message": "Аккаунт активирован, вы успешно вошли в систему."},
    )
