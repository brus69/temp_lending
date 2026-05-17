from datetime import timedelta

from django.db import migrations
from django.utils import timezone


ARTICLE_ROWS = [
    ("Как выбрать метизы для стройки", "kak-vybrat-metizy"),
    ("Анкерный крепёж: виды и применение", "ankernyj-krepezh"),
    ("Нержавеющая сталь в крепеже", "nerzhaveyushchaya-stal"),
    ("Хранение крепежа на складе", "hranenie-krepezha"),
    ("Саморезы по дереву и металлу", "samorezy-derevo-metall"),
    ("Дюбели для газобетона", "dyubeli-gazobeton"),
    ("Такелажные элементы: безопасность", "takelazh-bezopasnost"),
    ("Химические анкеры: инструкция", "himicheskie-ankery"),
    ("Крепёж для автомобильной отрасли", "krepezh-avto"),
    ("Монтажные ленты в ремонте", "montazhnye-lenty-remont"),
]

NEWS_ROWS = [
    ("Открытие нового склада в Подмосковье", "sklad-podmoskove"),
    ("Расширение ассортимента метизов", "assortiment-metizy"),
    ("Партнёрство с производителем DIN", "partnerstvo-din"),
    ("Обновление каталога такелажа", "katalog-takelazh"),
    ("Скидки для оптовых клиентов", "skidki-opt"),
    ("Новая линейка пластикового крепежа", "plastik-krepezh"),
    ("Сервис доставки в регионы", "dostavka-regiony"),
    ("Выставка «Стройка и ремонт»", "vystavka-stroyka"),
    ("Обучение менеджеров по продукции", "obuchenie-menedzhery"),
    ("Итоги года: рост продаж", "itogi-goda"),
]

PROMOTION_ROWS = [
    ("Скидка 15% на метизы", "skidka-15-metizy"),
    ("2+1 на саморезы", "2plus1-samorezy"),
    ("Бесплатная доставка от 5000 ₽", "besplatnaya-dostavka-5000"),
    ("Распродажа такелажа", "rasprodazha-takelazh"),
    ("Промокод ВЕСНА2026", "promokod-vesna2026"),
    ("Комплект крепежа со скидкой", "komplekt-krepezh"),
    ("Акция для юрлиц", "akciya-yurlica"),
    ("Неделя химического крепежа", "nedelya-himkrepezh"),
    ("Скидка на первый заказ", "skidka-pervyj-zakaz"),
    ("Оптом дешевле: до −20%", "optom-minus-20"),
]


def _create_items(model, rows, now):
    for idx, (title, slug) in enumerate(rows, start=1):
        if model.objects.filter(slug=slug).exists():
            continue
        model.objects.create(
            title=title,
            slug=slug,
            excerpt=f"{title}. Краткое описание для каталога материалов.",
            body=f"<p>{title}</p><p>Материал подготовлен редакцией магазина.</p>",
            is_published=True,
            published_at=now - timedelta(days=idx),
        )


def seed_content_pages(apps, schema_editor):
    now = timezone.now()
    _create_items(apps.get_model("shop", "Article"), ARTICLE_ROWS, now)
    _create_items(apps.get_model("shop", "News"), NEWS_ROWS, now)
    _create_items(apps.get_model("shop", "Promotion"), PROMOTION_ROWS, now)


def unseed_content_pages(apps, schema_editor):
    apps.get_model("shop", "Article").objects.filter(
        slug__in=[slug for _, slug in ARTICLE_ROWS],
    ).delete()
    apps.get_model("shop", "News").objects.filter(
        slug__in=[slug for _, slug in NEWS_ROWS],
    ).delete()
    apps.get_model("shop", "Promotion").objects.filter(
        slug__in=[slug for _, slug in PROMOTION_ROWS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0019_content_pages"),
    ]

    operations = [
        migrations.RunPython(seed_content_pages, unseed_content_pages),
    ]
