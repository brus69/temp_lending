from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect, render

from .models import Category, Product


def _seed_demo_data() -> None:
    if Category.objects.exists():
        return

    categories_data = [
        ("Метизы", "metizy", 438150, "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=260&q=80"),
        ("Скобяные изделия и фурнитура", "furnitura", 104522, "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=260&q=80"),
        ("Специальный крепеж", "special-krepezh", 96788, "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=260&q=80"),
        ("Такелаж", "takelazh", 64732, "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=260&q=80"),
        ("Пластиковый крепеж", "plastic-krepezh", 28878, "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=260&q=80"),
        ("Автомобильный крепеж", "auto-krepezh", 5246, "https://images.unsplash.com/photo-1611835151646-5a9df7f11463?auto=format&fit=crop&w=260&q=80"),
        ("Монтажные ленты", "montazhnye-lenty", 17715, "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=260&q=80"),
        ("Химический", "chemical", 13699, "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=260&q=80"),
    ]
    categories = []
    for idx, (name, slug, count, image_url) in enumerate(categories_data, start=1):
        categories.append(
            Category.objects.create(
                name=name,
                slug=slug,
                product_count=count,
                image_url=image_url,
                sort_order=idx,
            )
        )

    metizy = categories[0]
    products_data = [
        ("Гайка DIN934 оцинкованная M10 50 шт", "gaika-din934-m10", "SKU-015361", Decimal("210.00"), Decimal("358.00"), "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=1200&q=80"),
        ("Шайба DIN9021 кузовная M8 100 шт", "shaiba-din9021-m8", "SKU-015362", Decimal("270.00"), Decimal("377.00"), "https://images.unsplash.com/photo-1616789079464-9274d77b2d1f?auto=format&fit=crop&w=700&q=80"),
        ("Гайка DIN934 оцинкованная M8 100 шт", "gaika-din934-m8", "SKU-015363", Decimal("191.00"), Decimal("314.00"), "https://images.unsplash.com/photo-1616788494707-ec28f08d05a1?auto=format&fit=crop&w=700&q=80"),
        ("Шпилька резьбовая DIN975", "shpilka-din975", "SKU-015364", Decimal("71.00"), Decimal("154.00"), "https://images.unsplash.com/photo-1609942072337-c3370e820d25?auto=format&fit=crop&w=700&q=80"),
    ]

    for name, slug, sku, price, old_price, image_url in products_data:
        Product.objects.create(
            category=metizy,
            name=name,
            slug=slug,
            sku=sku,
            price=price,
            old_price=old_price,
            image_url=image_url,
            description="Надежный крепеж для строительных и монтажных задач.",
            specs={
                "Диаметр резьбы": "M10",
                "Шаг резьбы": "1.5",
                "Направление резьбы": "правая",
                "Размер под ключ": "17 мм",
                "Фасовка": "50 шт",
                "DIN": "934",
                "Материал": "сталь",
                "Покрытие": "цинк",
            },
            reviews_count=88,
            stock_store=120,
            stock_warehouse=260,
        )


def index(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)[:6]
    promo_products = Product.objects.all()[:4]
    return render(request, "shop/index.html", {"categories": categories, "promo_products": promo_products})


def category(request):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    return render(request, "shop/category.html", {"categories": categories})


def sub_category(request, slug=None):
    _seed_demo_data()
    categories = Category.objects.filter(is_featured=True)
    current_category = Category.objects.filter(slug=slug).first() if slug else categories.first()
    products = Product.objects.filter(category=current_category) if current_category else Product.objects.none()
    return render(
        request,
        "shop/sub_category.html",
        {"categories": categories, "current_category": current_category, "products": products},
    )


def product_detail(request, slug=None):
    _seed_demo_data()
    if not slug:
        first = Product.objects.first()
        if not first:
            return redirect("index")
        return redirect("product_detail", slug=first.slug)
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, "shop/product_detail.html", {"product": product, "related_products": related_products})
