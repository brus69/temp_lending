from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Администрирование LendingStore"
admin.site.site_title = "LendingStore — админка"
admin.site.index_title = "Панель управления"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("shop.urls")),
]

if settings.DEBUG or getattr(settings, "SERVE_MEDIA", False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
