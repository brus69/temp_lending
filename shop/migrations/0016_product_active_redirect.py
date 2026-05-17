import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0015_product_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Товар активен"),
        ),
        migrations.AddField(
            model_name="product",
            name="redirect_product",
            field=models.ForeignKey(
                blank=True,
                help_text="Обязательно, если товар неактивен: посетитель будет перенаправлен на выбранный товар.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="inactive_redirect_sources",
                to="shop.product",
                verbose_name="Редирект 301 на товар",
            ),
        ),
    ]
