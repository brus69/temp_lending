from django.db import migrations, models


def enable_top_menu_for_featured(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Category.objects.filter(is_featured=True).update(show_in_top_menu=True)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0017_category_default_listing_view"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="show_in_top_menu",
            field=models.BooleanField(
                default=False,
                help_text="Показывать ссылку на категорию в горизонтальной полосе под шапкой сайта.",
                verbose_name="Верхнее меню",
            ),
        ),
        migrations.RunPython(enable_top_menu_for_featured, migrations.RunPython.noop),
    ]
