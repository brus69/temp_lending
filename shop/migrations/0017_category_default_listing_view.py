from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0016_product_active_redirect"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="default_listing_view",
            field=models.CharField(
                choices=[("grid", "Плитка"), ("list", "Список")],
                default="grid",
                help_text="Как показывать каталог этой категории при первом открытии страницы.",
                max_length=8,
                verbose_name="Отображение товаров по умолчанию",
            ),
        ),
    ]
