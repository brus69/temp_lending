from django.db import migrations, models


TOP_MENU_ROWS = [
    ("Получение и оплата", "", 10),
    ("Сервис и поддержка", "", 20),
    ("О нас", "", 30),
]


def seed_top_menu_links(apps, schema_editor):
    TopMenuLink = apps.get_model("shop", "TopMenuLink")
    for title, url, sort_order in TOP_MENU_ROWS:
        TopMenuLink.objects.get_or_create(
            title=title,
            defaults={"url": url, "sort_order": sort_order, "is_active": True},
        )


def unseed_top_menu_links(apps, schema_editor):
    apps.get_model("shop", "TopMenuLink").objects.filter(
        title__in=[row[0] for row in TOP_MENU_ROWS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0023_yandex_feed_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="TopMenuLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120, verbose_name="Название")),
                (
                    "url",
                    models.CharField(
                        blank=True,
                        help_text="Путь на сайте (/articles/) или полный URL. Пусто — текст без ссылки.",
                        max_length=500,
                        verbose_name="Ссылка",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать")),
                ("open_in_new_tab", models.BooleanField(default=False, verbose_name="Новая вкладка")),
            ],
            options={
                "verbose_name": "Пункт верхнего меню",
                "verbose_name_plural": "Верхнее меню",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_top_menu_links, unseed_top_menu_links),
    ]
