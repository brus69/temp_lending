"""Помощники для подбора менеджера по категории товара."""

from __future__ import annotations

import re

from django.conf import settings

from shop.models import Category, Manager


def phone_to_tel(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("8"):
        return f"+7{digits[1:]}"
    if len(digits) == 11 and digits.startswith("7"):
        return f"+{digits}"
    return f"+{digits}" if digits else ""


def get_managers_for_category(category: Category | None):
    """Менеджеры, привязанные к категории; если нет — любой активный (запасной)."""
    base_qs = Manager.objects.filter(is_active=True).order_by("sort_order", "name")
    if category is None:
        return base_qs
    linked = base_qs.filter(categories=category)
    if linked.exists():
        return linked
    return base_qs


def get_primary_manager_for_category(category: Category | None) -> Manager | None:
    return get_managers_for_category(category).first()


def default_manager_photo_url() -> str:
    return getattr(
        settings,
        "EXPERT_HELP_PHOTO_URL",
        "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=240&h=280&q=80",
    )
