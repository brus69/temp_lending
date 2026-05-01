from django import forms
from django.contrib import admin

from .models import (
    Category,
    CategorySpecAttribute,
    Favorite,
    Order,
    OrderItem,
    Organization,
    Product,
    ProductQuestion,
    ProductReview,
    ProductReviewPhoto,
    ProductSpecValue,
    UserProfile,
)


class CategorySpecAttributeInline(admin.TabularInline):
    model = CategorySpecAttribute
    extra = 1
    ordering = ("sort_order", "id")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count", "is_featured", "sort_order")
    list_editable = ("product_count", "is_featured", "sort_order")
    search_fields = ("name", "slug")
    inlines = [CategorySpecAttributeInline]
    fieldsets = (
        (None, {"fields": ("name", "slug", "product_count", "image_url", "is_featured", "sort_order")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )


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


class ProductSpecValueInline(admin.TabularInline):
    model = ProductSpecValue
    extra = 1

    def get_formset(self, request, obj=None, **kwargs):
        category_id = obj.category_id if obj else None

        class ProductSpecValueAdminForm(forms.ModelForm):
            class Meta:
                model = ProductSpecValue
                fields = "__all__"

            def __init__(self, *args, **form_kw):
                super().__init__(*args, **form_kw)
                qs = (
                    CategorySpecAttribute.objects.filter(category_id=category_id).order_by("sort_order", "id")
                    if category_id
                    else CategorySpecAttribute.objects.none()
                )
                self.fields["attribute"].queryset = qs

        kwargs.setdefault("form", ProductSpecValueAdminForm)
        return super().get_formset(request, obj, **kwargs)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "old_price", "is_best_price")
    list_filter = ("category", "is_best_price")
    search_fields = ("name", "sku", "slug")
    inlines = [ProductSpecValueInline]
    readonly_fields = ("specs", "rating", "reviews_count")
    fieldsets = (
        (None, {"fields": ("category", "name", "slug", "sku", "price", "old_price", "image_url", "description")}),
        ("SEO", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
        ("Остатки и метки", {"fields": ("stock_store", "stock_warehouse", "is_best_price")}),
        ("Рейтинг (авто)", {"fields": ("rating", "reviews_count")}),
        ("Устаревший JSON", {"classes": ("collapse",), "fields": ("specs",)}),
    )

    def save_model(self, request, obj, form, change):
        prev_cat = None
        if change and obj.pk:
            prev_cat = Product.objects.filter(pk=obj.pk).values_list("category_id", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and prev_cat is not None and prev_cat != obj.category_id:
            ProductSpecValue.objects.filter(product=obj).exclude(attribute__category_id=obj.category_id).delete()


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
