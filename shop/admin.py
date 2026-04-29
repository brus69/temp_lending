from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count", "is_featured", "sort_order")
    list_editable = ("product_count", "is_featured", "sort_order")
    search_fields = ("name", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "old_price", "is_best_price")
    list_filter = ("category", "is_best_price")
    search_fields = ("name", "sku", "slug")
