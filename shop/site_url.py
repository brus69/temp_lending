from urllib.parse import urlparse

from django.conf import settings


def get_public_base_url(request=None) -> str:
    """Базовый URL сайта без завершающего слэша."""
    raw = getattr(settings, "PUBLIC_SITE_URL", "").strip()
    if raw:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        if parsed.netloc:
            return f"{parsed.scheme or 'https'}://{parsed.netloc}"

    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")

    try:
        from django.contrib.sites.models import Site

        domain = Site.objects.get_current().domain
    except Exception:
        domain = "example.com"
    return f"https://{domain}"


def build_absolute_url(path: str, request=None) -> str:
    """Собирает абсолютный URL из базы и пути или полной ссылки."""
    path = (path or "").strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    base = get_public_base_url(request)
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"
