from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from shop.models import Article, Category, News, Product, Promotion, TopMenuLink


def _public_site_parts() -> tuple[str, str] | None:
    """(protocol, domain) из DJANGO_PUBLIC_SITE_URL, например https://shop.example.com."""
    raw = getattr(settings, "PUBLIC_SITE_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if not parsed.netloc:
        return None
    protocol = parsed.scheme or "https"
    return protocol, parsed.netloc


class LendingStoreSitemap(Sitemap):
    """Базовый sitemap: домен из DJANGO_PUBLIC_SITE_URL или django.contrib.sites."""

    def get_protocol(self, protocol=None):
        parts = _public_site_parts()
        if parts:
            return parts[0]
        return super().get_protocol(protocol)

    def get_domain(self, site=None):
        parts = _public_site_parts()
        if parts:
            return parts[1]
        return super().get_domain(site)


class StaticViewSitemap(LendingStoreSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "index",
            "category",
            "article_list",
            "news_list",
            "promotion_list",
        ]

    def location(self, item):
        return reverse(item)


class TopMenuLinkSitemap(LendingStoreSitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return TopMenuLink.objects.filter(is_active=True).only("slug", "updated_at")

    def location(self, obj):
        return reverse("top_menu_page", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(LendingStoreSitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return reverse("sub_category_by_slug", args=[obj.slug])


class ProductSitemap(LendingStoreSitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.active().only("slug")

    def location(self, obj):
        return reverse("product_detail", args=[obj.slug])


class PublishedContentSitemap(LendingStoreSitemap):
    changefreq = "weekly"
    priority = 0.6

    def __init__(self, model, detail_view_name: str):
        self.model = model
        self.detail_view_name = detail_view_name

    def items(self):
        return (
            self.model.objects.filter(is_published=True)
            .only("slug", "updated_at")
            .order_by("-updated_at", "-pk")
        )

    def location(self, obj):
        return reverse(self.detail_view_name, args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


article_sitemap = PublishedContentSitemap(Article, "article_detail")
news_sitemap = PublishedContentSitemap(News, "news_detail")
promotion_sitemap = PublishedContentSitemap(Promotion, "promotion_detail")
