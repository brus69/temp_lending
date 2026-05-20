from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from shop.sitemaps import (
    CategorySitemap,
    ProductSitemap,
    StaticViewSitemap,
    TopMenuLinkSitemap,
    article_sitemap,
    news_sitemap,
    promotion_sitemap,
)

admin.site.site_header = "Администрирование LendingStore"
admin.site.site_title = "LendingStore — админка"
admin.site.index_title = "Панель управления"

sitemaps = {
    "static": StaticViewSitemap,
    "info": TopMenuLinkSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
    "articles": article_sitemap,
    "news": news_sitemap,
    "promotions": promotion_sitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("shop.urls")),
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
