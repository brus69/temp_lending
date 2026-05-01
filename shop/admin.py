from django.contrib import admin

from .models import (
    Category,
    Favorite,
    Order,
    OrderItem,
    Organization,
    Product,
    ProductQuestion,
    ProductReview,
    ProductReviewPhoto,
    UserProfile,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count", "is_featured", "sort_order")
    list_editable = ("product_count", "is_featured", "sort_order")
    search_fields = ("name", "slug")


class ProductReviewPhotoInline(admin.TabularInline):
    model = ProductReviewPhoto
    extra = 0


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user__email", "text")
    inlines = [ProductReviewPhotoInline]


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "created_at", "answered_at")
    list_filter = ("created_at", "answered_at")
    search_fields = ("product__name", "text", "answer_text")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "old_price", "is_best_price")
    list_filter = ("category", "is_best_price")
    search_fields = ("name", "sku", "slug")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone", "total_price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "phone", "email")
    inlines = [OrderItemInline]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__username", "product__name", "product__sku")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "delivery_address")
    search_fields = ("user__email", "user__username", "phone", "delivery_address")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "inn", "kpp", "owner", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "inn", "kpp", "owner__email", "owner__username")
