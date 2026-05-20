import shop.models
from django.db import migrations, models


CERTIFICATE_URL = (
    "https://images.unsplash.com/photo-1586281380349-632531db7ed4?auto=format&fit=crop&w=400&h=560&q=80"
)
THANK_YOU_URL = (
    "https://images.unsplash.com/photo-1586953208448-b95a79798f07?auto=format&fit=crop&w=400&h=560&q=80"
)


def seed_homepage_documents(apps, schema_editor):
    HomepageDocument = apps.get_model("shop", "HomepageDocument")
    if HomepageDocument.objects.exists():
        return
    for i in range(6):
        HomepageDocument.objects.create(
            kind="certificate",
            title=f"Сертификат {i + 1}",
            image_url=CERTIFICATE_URL,
            sort_order=i,
            is_active=True,
        )
    for i in range(5):
        HomepageDocument.objects.create(
            kind="thank_you",
            title=f"Благодарность {i + 1}",
            image_url=THANK_YOU_URL,
            sort_order=i,
            is_active=True,
        )


def unseed_homepage_documents(apps, schema_editor):
    apps.get_model("shop", "HomepageDocument").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0027_manager"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomepageDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("certificate", "Сертификат"),
                            ("thank_you", "Благодарственное письмо"),
                        ],
                        db_index=True,
                        max_length=20,
                        verbose_name="Тип",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        blank=True,
                        help_text="Необязательно. Используется в alt у изображения.",
                        max_length=200,
                        verbose_name="Подпись",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to=shop.models.homepage_document_upload_to,
                        verbose_name="Изображение",
                    ),
                ),
                (
                    "image_url",
                    models.URLField(
                        blank=True,
                        help_text="Если файл не загружен, используется эта ссылка.",
                        max_length=500,
                        verbose_name="URL изображения",
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Порядок")),
                ("is_active", models.BooleanField(default=True, verbose_name="Показывать на главной")),
            ],
            options={
                "verbose_name": "Документ на главной",
                "verbose_name_plural": "Документы на главной",
                "ordering": ["kind", "sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_homepage_documents, unseed_homepage_documents),
    ]
