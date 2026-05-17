from django.db import migrations, models


def forwards_migrate_labels(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    ProductLabel = apps.get_model("shop", "ProductLabel")

    defaults = [
        {
            "slug": "best-price",
            "name": "Лучшая цена",
            "background_class": "bg-sky-500",
            "sort_order": 1,
            "detail_banner_text": "Лучшая цена. Ниже средней рыночной",
        },
        {
            "slug": "closed-sale",
            "name": "Закрытая распродажа",
            "background_class": "bg-violet-600",
            "sort_order": 2,
            "detail_banner_text": "",
        },
        {
            "slug": "new",
            "name": "Новинка",
            "background_class": "bg-emerald-600",
            "sort_order": 3,
            "detail_banner_text": "",
        },
    ]
    label_by_slug = {}
    for item in defaults:
        label, _ = ProductLabel.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "background_class": item["background_class"],
                "sort_order": item["sort_order"],
                "detail_banner_text": item["detail_banner_text"],
                "text_class": "text-white",
            },
        )
        label_by_slug[item["slug"]] = label

    for product in Product.objects.all():
        labels = []
        if getattr(product, "is_best_price", False):
            labels.append(label_by_slug["best-price"])
        if getattr(product, "is_closed_sale", False):
            labels.append(label_by_slug["closed-sale"])
        if getattr(product, "is_new", False):
            labels.append(label_by_slug["new"])
        if labels:
            product.labels.set(labels)


def backwards_migrate_labels(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    ProductLabel = apps.get_model("shop", "ProductLabel")
    label_by_slug = {label.slug: label for label in ProductLabel.objects.all()}

    for product in Product.objects.all():
        slugs = set(product.labels.values_list("slug", flat=True))
        product.is_best_price = "best-price" in slugs
        product.is_closed_sale = "closed-sale" in slugs
        product.is_new = "new" in slugs
        product.save(update_fields=["is_best_price", "is_closed_sale", "is_new"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0014_product_sale_new_badges"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductLabel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64, unique=True, verbose_name="Название")),
                ("slug", models.SlugField(blank=True, max_length=64, unique=True, verbose_name="Слаг")),
                (
                    "background_class",
                    models.CharField(
                        default="bg-sky-500",
                        help_text="Например: bg-sky-500, bg-violet-600",
                        max_length=96,
                        verbose_name="Класс фона (Tailwind)",
                    ),
                ),
                (
                    "text_class",
                    models.CharField(
                        blank=True,
                        default="text-white",
                        max_length=96,
                        verbose_name="Класс текста (Tailwind)",
                    ),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Порядок")),
                (
                    "detail_banner_text",
                    models.CharField(
                        blank=True,
                        help_text="Необязательный информационный блок на карточке товара.",
                        max_length=255,
                        verbose_name="Текст на странице товара",
                    ),
                ),
            ],
            options={
                "verbose_name": "Метка товара",
                "verbose_name_plural": "Метки товаров",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="labels",
            field=models.ManyToManyField(
                blank=True,
                related_name="products",
                to="shop.productlabel",
                verbose_name="Метки",
            ),
        ),
        migrations.RunPython(forwards_migrate_labels, backwards_migrate_labels),
        migrations.RemoveField(model_name="product", name="is_best_price"),
        migrations.RemoveField(model_name="product", name="is_closed_sale"),
        migrations.RemoveField(model_name="product", name="is_new"),
    ]
