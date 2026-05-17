from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count, Prefetch
from django.utils.text import slugify


def product_image_upload_to(instance: "Product", filename: str) -> str:
    """Файлы в media/products/<slug_категории>/<slug_товара>.<ext>"""
    ext = Path(filename).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if ext not in allowed:
        ext = ".jpg"
    cat_slug = "unsorted"
    if instance.category_id:
        cat = instance.category
        cat_slug = getattr(cat, "slug", None) or str(instance.category_id)
    base = instance.slug or (str(instance.pk) if instance.pk else "draft")
    return f"products/{cat_slug}/{base}{ext}"


def product_gallery_image_upload_to(instance: "ProductGalleryImage", filename: str) -> str:
    """Файлы галереи: media/products/<slug_категории>/gallery/<slug_товара>-<id>.<ext>"""
    ext = Path(filename).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if ext not in allowed:
        ext = ".jpg"
    cat_slug = "unsorted"
    if instance.product_id:
        cat_slug = (
            getattr(instance.product.category, "slug", None)
            or str(instance.product.category_id)
            or "unsorted"
        )
    base = (
        instance.product.slug
        if instance.product_id and instance.product.slug
        else str(instance.product_id or "draft")
    )
    suffix = str(instance.pk) if instance.pk else "new"
    return f"products/{cat_slug}/gallery/{base}-{suffix}{ext}"


def category_image_upload_to(instance: "Category", filename: str) -> str:
    """Файлы категорий: media/categories/<slug>.<ext>"""
    ext = Path(filename).suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    if ext not in allowed:
        ext = ".jpg"
    base = instance.slug or (str(instance.pk) if instance.pk else "draft")
    return f"categories/{base}{ext}"


class Category(models.Model):
    name = models.CharField("Название", max_length=120)
    slug = models.SlugField("Слаг", unique=True)
    meta_title = models.CharField(
        "SEO — title",
        max_length=255,
        blank=True,
        help_text="Заголовок страницы в браузере и для поисковиков. Пусто — используется название категории.",
    )
    meta_description = models.CharField(
        "SEO — description",
        max_length=320,
        blank=True,
        help_text="Мета-описание для поиска (рекомендуется до ~320 символов).",
    )
    product_count = models.PositiveIntegerField("Товаров в каталоге", default=0)
    image = models.ImageField(
        "Изображение (загрузка)",
        upload_to=category_image_upload_to,
        blank=True,
        null=True,
        help_text="Если файл загружен, он имеет приоритет над URL.",
    )
    image_url = models.URLField("URL изображения", blank=True)
    is_featured = models.BooleanField("Показывать на главной", default=True)
    sort_order = models.PositiveIntegerField("Порядок сортировки", default=0)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def primary_image_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except ValueError:
                pass
        return (self.image_url or "").strip()


class CategorySpecAttribute(models.Model):
    """Набор названий характеристик для категории (шаблон для товаров)."""

    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.CASCADE,
        related_name="spec_attributes",
    )
    name = models.CharField("Название", max_length=120)
    sort_order = models.PositiveIntegerField("Порядок отображения", default=0)

    class Meta:
        verbose_name = "Характеристика категории"
        verbose_name_plural = "Характеристики категории"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="uniq_category_spec_attribute_name"),
        ]

    def __str__(self) -> str:
        return f"{self.category.slug}: {self.name}"


class ProductLabel(models.Model):
    """Настраиваемая метка для карточки товара (создаётся в админке)."""

    name = models.CharField("Название", max_length=64, unique=True)
    slug = models.SlugField("Слаг", max_length=64, unique=True, blank=True)
    background_class = models.CharField(
        "Класс фона (Tailwind)",
        max_length=96,
        default="bg-sky-500",
        help_text="Например: bg-sky-500, bg-violet-600",
    )
    text_class = models.CharField(
        "Класс текста (Tailwind)",
        max_length=96,
        default="text-white",
        blank=True,
    )
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)
    detail_banner_text = models.CharField(
        "Текст на странице товара",
        max_length=255,
        blank=True,
        help_text="Необязательный информационный блок на карточке товара.",
    )

    class Meta:
        verbose_name = "Метка товара"
        verbose_name_plural = "Метки товаров"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or "label"
            slug = base
            counter = 1
            while ProductLabel.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)


def product_labels_prefetch() -> Prefetch:
    return Prefetch("labels", queryset=ProductLabel.objects.order_by("sort_order", "name"))


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("Слаг", unique=True)
    sku = models.CharField("Артикул (SKU)", max_length=64, unique=True)
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    old_price = models.DecimalField("Старая цена", max_digits=10, decimal_places=2, null=True, blank=True)
    image = models.ImageField(
        "Изображение (загрузка)",
        upload_to=product_image_upload_to,
        blank=True,
        null=True,
        help_text="Каталог на сервере: products/<slug категории>/файл. Если файл загружен, он имеет приоритет над URL.",
    )
    image_url = models.URLField(
        "URL изображения",
        blank=True,
        help_text="Внешняя ссылка. Обязательно, если файл не загружен.",
    )
    description = models.TextField("Описание", blank=True)
    meta_title = models.CharField(
        "SEO — title",
        max_length=255,
        blank=True,
        help_text="Заголовок вкладки и для поисковиков. Пусто — используется название товара.",
    )
    meta_description = models.CharField(
        "SEO — description",
        max_length=320,
        blank=True,
        help_text="Мета description для поиска (рекомендуется до ~320 символов).",
    )
    specs = models.JSONField(
        "Характеристики (JSON, устар.)",
        default=dict,
        blank=True,
        help_text="Не используйте для новых данных — задайте характеристики категории и значения у товара.",
    )
    rating = models.DecimalField("Рейтинг", max_digits=3, decimal_places=1, default=5.0)
    reviews_count = models.PositiveIntegerField("Количество отзывов", default=0)
    stock_store = models.PositiveIntegerField("Остаток в магазинах", default=0)
    stock_warehouse = models.PositiveIntegerField("Остаток на складе", default=0)
    labels = models.ManyToManyField(
        ProductLabel,
        verbose_name="Метки",
        blank=True,
        related_name="products",
    )
    is_active = models.BooleanField("Товар активен", default=True)
    redirect_product = models.ForeignKey(
        "self",
        verbose_name="Редирект 301 на товар",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inactive_redirect_sources",
        help_text="Обязательно, если товар неактивен: посетитель будет перенаправлен на выбранный товар.",
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        has_file = bool(getattr(self, "image", False) and getattr(self.image, "name", ""))
        has_url = bool((self.image_url or "").strip())
        if not has_file and not has_url:
            raise ValidationError(
                {
                    "image": "Укажите загруженное изображение или URL.",
                    "image_url": "Укажите URL или загрузите файл.",
                },
            )
        if not self.is_active:
            if not self.redirect_product_id:
                raise ValidationError(
                    {"redirect_product": "Для неактивного товара укажите товар для редиректа 301."},
                )
            if self.pk and self.redirect_product_id == self.pk:
                raise ValidationError({"redirect_product": "Товар не может перенаправлять на самого себя."})
            target = self.redirect_product
            if target and not target.is_active:
                raise ValidationError({"redirect_product": "Целевой товар должен быть активным."})
        elif self.redirect_product_id:
            raise ValidationError(
                {"redirect_product": "Редирект задаётся только для неактивного товара."},
            )

    @property
    def primary_image_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except ValueError:
                pass
        return (self.image_url or "").strip()

    def ordered_spec_values(self):
        """Значения характеристик с предзагрузкой атрибута, по порядку категории."""
        return (
            self.spec_values.select_related("attribute")
            .order_by("attribute__sort_order", "attribute__id")
        )

    def refresh_review_aggregate(self) -> None:
        """Пересчёт средней оценки и количества отзывов из таблицы отзывов."""
        agg = self.reviews.aggregate(cnt=Count("id"), avg=Avg("rating"))
        cnt = agg["cnt"] or 0
        self.reviews_count = cnt
        if cnt == 0:
            self.rating = Decimal("5.0")
        else:
            self.rating = Decimal(str(round(float(agg["avg"]), 1)))
        self.save(update_fields=["reviews_count", "rating"])


class ProductSpecValue(models.Model):
    """Значение одной характеристики у товара (атрибут задаётся на категории)."""

    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        on_delete=models.CASCADE,
        related_name="spec_values",
    )
    attribute = models.ForeignKey(
        CategorySpecAttribute,
        verbose_name="Характеристика",
        on_delete=models.CASCADE,
        related_name="product_values",
    )
    value = models.CharField("Значение", max_length=512)

    class Meta:
        verbose_name = "Значение характеристики"
        verbose_name_plural = "Значения характеристик"
        constraints = [
            models.UniqueConstraint(fields=["product", "attribute"], name="uniq_product_spec_value_attribute"),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}: {self.attribute.name}"

    def clean(self) -> None:
        super().clean()
        if self.attribute_id and self.product_id:
            if self.attribute.category_id != self.product.category_id:
                raise ValidationError(
                    {"attribute": "Выберите характеристику из категории этого товара."},
                )


class ProductGalleryImage(models.Model):
    MAX_IMAGES_PER_PRODUCT = 10

    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    image = models.ImageField("Фото", upload_to=product_gallery_image_upload_to)
    sort_order = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товара"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"Фото {self.product_id} #{self.id or 'new'}"

    def clean(self) -> None:
        super().clean()
        if not self.product_id:
            return
        current_count = (
            ProductGalleryImage.objects
            .filter(product_id=self.product_id)
            .exclude(pk=self.pk)
            .count()
        )
        if current_count >= self.MAX_IMAGES_PER_PRODUCT:
            raise ValidationError(
                {"product": f"Можно загрузить не более {self.MAX_IMAGES_PER_PRODUCT} изображений на товар."},
            )


def sync_product_specs_from_json(product: Product) -> bool:
    """Переносит product.specs в ProductSpecValue и обнуляет JSON. Возвращает True, если были данные."""
    raw = product.specs or {}
    if not raw:
        return False
    if product.spec_values.exists():
        return False
    for idx, (name, val) in enumerate(raw.items()):
        attr, _created = CategorySpecAttribute.objects.get_or_create(
            category=product.category,
            name=name,
            defaults={"sort_order": idx},
        )
        ProductSpecValue.objects.update_or_create(
            product=product,
            attribute=attr,
            defaults={"value": str(val)},
        )
    Product.objects.filter(pk=product.pk).update(specs={})
    return True


class ProductReview(models.Model):
    MAX_TEXT_LEN = 3000
    MAX_PHOTOS = 5

    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField("Оценка")
    text = models.TextField("Текст отзыва", max_length=MAX_TEXT_LEN)
    created_at = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв о товаре"
        verbose_name_plural = "Отзывы о товарах"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_product_review_per_user"),
        ]

    def __str__(self) -> str:
        return f"Отзыв {self.user_id} → {self.product_id}"


class ProductReviewPhoto(models.Model):
    review = models.ForeignKey(
        ProductReview,
        verbose_name="Отзыв",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField("Изображение", upload_to="product_reviews/%Y/%m/")

    class Meta:
        verbose_name = "Фото к отзыву"
        verbose_name_plural = "Фото к отзывам"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"Фото к отзыву {self.review_id}"


class ProductQuestion(models.Model):
    MAX_TEXT_LEN = 2000

    product = models.ForeignKey(
        Product,
        verbose_name="Товар",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="product_questions",
    )
    text = models.TextField("Вопрос", max_length=MAX_TEXT_LEN)
    answer_text = models.TextField("Ответ магазина", blank=True)
    created_at = models.DateTimeField("Дата вопроса", auto_now_add=True)
    answered_at = models.DateTimeField("Дата ответа", null=True, blank=True)

    class Meta:
        verbose_name = "Вопрос о товаре"
        verbose_name_plural = "Вопросы о товарах"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Вопрос {self.user_id} → {self.product_id}"


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

    customer_name = models.CharField("Имя клиента", max_length=120)
    phone = models.CharField("Телефон", max_length=32)
    email = models.EmailField("Электронная почта", blank=True)
    address = models.CharField("Адрес", max_length=255)
    comment = models.TextField("Комментарий", blank=True)
    total_price = models.DecimalField("Сумма заказа", max_digits=12, decimal_places=2)
    status = models.CharField("Статус", max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Заказ #{self.id} - {self.customer_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(Product, verbose_name="Товар", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField("Количество", default=1)
    unit_price = models.DecimalField("Цена за единицу", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        "Product",
        verbose_name="Товар",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField("Добавлено", auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="uniq_favorite_user_product"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.product_id}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField("Телефон", max_length=32, blank=True)
    delivery_address = models.TextField("Адрес доставки", blank=True)

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self) -> str:
        return f"Профиль {self.user_id}"


class Organization(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Владелец",
        on_delete=models.CASCADE,
        related_name="organizations",
    )
    name = models.CharField("Название организации", max_length=255)
    inn = models.CharField("ИНН", max_length=12)
    kpp = models.CharField("КПП", max_length=9, blank=True)
    legal_address = models.CharField("Юридический адрес", max_length=255, blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "inn"], name="uniq_org_owner_inn"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.inn})"
