from datetime import timedelta

from django.db import migrations
from django.utils import timezone


CARD_IMAGES = [
    "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1599948128020-9a44505b3a80?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1611835151646-5a9df7f11463?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1585298723682-7115561c51b7?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1620432468734-65f36cf65dfa?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&q=80",
]


def fill_content_visuals(apps, schema_editor):
    today = timezone.localdate()
    for model_name in ("Article", "News", "Promotion"):
        model = apps.get_model("shop", model_name)
        for idx, item in enumerate(model.objects.order_by("id")):
            changed = False
            if not item.image_url:
                item.image_url = CARD_IMAGES[idx % len(CARD_IMAGES)]
                changed = True
            if not item.start_date:
                item.start_date = today - timedelta(days=idx * 4 + 1)
                changed = True
            if not item.end_date:
                item.end_date = item.start_date + timedelta(days=23)
                changed = True
            if changed:
                item.save(update_fields=["image_url", "start_date", "end_date"])


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0021_content_page_visuals"),
    ]

    operations = [
        migrations.RunPython(fill_content_visuals, migrations.RunPython.noop),
    ]
