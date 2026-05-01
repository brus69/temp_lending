from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import ProductQuestion, ProductReview


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ("rating", "text")
        widgets = {
            "rating": forms.HiddenInput(
                attrs={
                    "id": "id_rating",
                    "class": "sr-only",
                    "autocomplete": "off",
                },
            ),
            "text": forms.Textarea(
                attrs={
                    "rows": 5,
                    "maxlength": ProductReview.MAX_TEXT_LEN,
                    "class": "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm",
                    "placeholder": "Расскажите о товаре — до 3000 символов",
                },
            ),
        }
        labels = {
            "rating": "Оценка",
            "text": "Текст отзыва",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].required = False

    def clean_rating(self):
        raw = self.cleaned_data.get("rating")
        if raw in (None, ""):
            raise ValidationError("Выберите оценку, нажимая на звёзды.")
        try:
            r = int(raw)
        except (TypeError, ValueError):
            raise ValidationError("Некорректная оценка.")
        if r < 1 or r > 5:
            raise ValidationError("Оценка должна быть от 1 до 5.")
        return r


class ProductQuestionForm(forms.ModelForm):
    class Meta:
        model = ProductQuestion
        fields = ("text",)
        labels = {"text": "Текст вопроса"}
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": ProductQuestion.MAX_TEXT_LEN,
                    "class": "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm",
                    "placeholder": "Ваш вопрос о товаре — до 2000 символов",
                },
            ),
        }


def validate_review_image_files(files: list) -> None:
    if len(files) > ProductReview.MAX_PHOTOS:
        raise ValidationError(f"Можно прикрепить не более {ProductReview.MAX_PHOTOS} фото.", code="too_many_images")
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    max_bytes = 8 * 1024 * 1024
    for f in files:
        name = getattr(f, "name", "") or ""
        ext = Path(name).suffix.lower()
        if ext not in allowed_ext:
            raise ValidationError(
                "Допустимы только файлы JPEG, PNG, WebP или GIF.",
                code="bad_type",
            )
        if hasattr(f, "size") and f.size > max_bytes:
            raise ValidationError("Каждый файл не должен превышать 8 МБ.", code="too_large")
