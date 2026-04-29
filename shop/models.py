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


class Order(models.Model):
    STATUS_NEW = "new"
    STATUS_PAID = "paid"
    STATUS_SENT = "sent"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_NEW, "Новый"),
        (STATUS_PAID, "Оплачен"),
        (STATUS_SENT, "Отправлен"),
        (STATUS_DONE, "Завершен"),
    ]

    customer_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255)
    comment = models.TextField(blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Заказ #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"
