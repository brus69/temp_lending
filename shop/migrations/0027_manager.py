import shop.models
from django.db import migrations, models


def seed_default_manager(apps, schema_editor):
    Manager = apps.get_model("shop", "Manager")
    Category = apps.get_model("shop", "Category")
    if Manager.objects.exists():
        return
    manager = Manager.objects.create(
        name="Максим",
        phone="+7 (812) 507-64-54",
        sort_order=0,
        is_active=True,
    )
    manager.categories.set(Category.objects.all())


def unseed_default_manager(apps, schema_editor):
    apps.get_model("shop", "Manager").objects.filter(name="Максим").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0026_alter_topmenulink_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="Manager",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="Имя")),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        help_text="Пусто — подставится телефон по умолчанию из настроек сайта.",
                        max_length=32,
                        verbose_name="Телефон",
                    ),
                ),
                (
                    "photo",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=shop.models.manager_photo_upload_to,
                        verbose_name="Фото (загрузка)",
                    ),
                ),
                (
                    "photo_url",
                    models.URLField(
                        blank=True,
                        help_text="Если файл не загружен, используется эта ссылка.",
                        max_length=500,
                        verbose_name="URL фото",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Активен")),
                (
                    "categories",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Категории, для товаров которых показывается этот менеджер.",
                        related_name="managers",
                        to="shop.category",
                        verbose_name="Категории",
                    ),
                ),
            ],
            options={
                "verbose_name": "Менеджер",
                "verbose_name_plural": "Менеджеры",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RunPython(seed_default_manager, unseed_default_manager),
    ]
