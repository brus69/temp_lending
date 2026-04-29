from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    product_count = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=64, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField()
    description = models.TextField(blank=True)
    specs = models.JSONField(default=dict, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    reviews_count = models.PositiveIntegerField(default=0)
    stock_store = models.PositiveIntegerField(default=0)
    stock_warehouse = models.PositiveIntegerField(default=0)
    is_best_price = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
