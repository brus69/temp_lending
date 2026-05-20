from django.db import migrations, models
from django.utils.text import slugify


PAGE_DATA = [
    (
        "Получение и оплата",
        "poluchenie-i-oplata",
        10,
        "<p>Здесь размещается информация о способах получения заказа и оплаты.</p>",
    ),
    (
        "Сервис и поддержка",
        "servis-i-podderzhka",
        20,
        "<p>Здесь размещается информация о сервисе и поддержке покупателей.</p>",
    ),
    (
        "О нас",
        "o-nas",
        30,
        "<p>Здесь размещается информация о компании.</p>",
    ),
]


def populate_content_fields(apps, schema_editor):
    TopMenuLink = apps.get_model("shop", "TopMenuLink")
    for title, slug, sort_order, body in PAGE_DATA:
        TopMenuLink.objects.filter(title=title).update(
            slug=slug,
            sort_order=sort_order,
            body=body,
            meta_title="",
            meta_description="",
        )
    for link in TopMenuLink.objects.all():
        if link.slug:
            continue
        link.slug = slugify(link.title, allow_unicode=True) or f"page-{link.pk}"
        if not link.body:
            link.body = f"<p>{link.title}</p>"
        link.save(update_fields=["slug", "body"])


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0024_top_menu_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="topmenulink",
            name="slug",
            field=models.SlugField(blank=True, max_length=160, null=True, verbose_name="Слаг"),
        ),
        migrations.AddField(
            model_name="topmenulink",
            name="meta_title",
            field=models.CharField(
                blank=True,
                help_text="Заголовок вкладки и для поисковиков. Пусто — используется название.",
                max_length=255,
                verbose_name="SEO — title",
            ),
        ),
        migrations.AddField(
            model_name="topmenulink",
            name="meta_description",
            field=models.CharField(
                blank=True,
                help_text="Мета-описание для поиска (рекомендуется до ~320 символов).",
                max_length=320,
                verbose_name="SEO — description",
            ),
        ),
        migrations.AddField(
            model_name="topmenulink",
            name="body",
            field=models.TextField(blank=True, default="", verbose_name="Текст страницы"),
        ),
        migrations.AddField(
            model_name="topmenulink",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Обновлено"),
        ),
        migrations.RunPython(populate_content_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="topmenulink",
            name="slug",
            field=models.SlugField(max_length=160, unique=True, verbose_name="Слаг"),
        ),
        migrations.AlterField(
            model_name="topmenulink",
            name="body",
            field=models.TextField(verbose_name="Текст страницы"),
        ),
        migrations.RemoveField(
            model_name="topmenulink",
            name="url",
        ),
        migrations.RemoveField(
            model_name="topmenulink",
            name="open_in_new_tab",
        ),
        migrations.AlterField(
            model_name="topmenulink",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Показывать в меню"),
        ),
        migrations.AlterField(
            model_name="topmenulink",
            name="sort_order",
            field=models.PositiveIntegerField(default=0, verbose_name="Порядок в меню"),
        ),
        migrations.AlterField(
            model_name="topmenulink",
            name="title",
            field=models.CharField(max_length=120, verbose_name="Название в меню"),
        ),
    ]
