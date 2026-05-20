"""Список городов и сопоставление с ответами геолокации по IP."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable

DEFAULT_CITY = "Москва"

REGIONAL_CENTERS_RU: tuple[str, ...] = (
    "Абакан",
    "Анадырь",
    "Архангельск",
    "Астрахань",
    "Барнаул",
    "Белгород",
    "Благовещенск",
    "Брянск",
    "Великий Новгород",
    "Владивосток",
    "Владикавказ",
    "Владимир",
    "Волгоград",
    "Вологда",
    "Воронеж",
    "Горно-Алтайск",
    "Грозный",
    "Екатеринбург",
    "Иваново",
    "Ижевск",
    "Иркутск",
    "Йошкар-Ола",
    "Казань",
    "Калининград",
    "Калуга",
    "Кемерово",
    "Киров",
    "Кострома",
    "Краснодар",
    "Красноярск",
    "Курган",
    "Курск",
    "Кызыл",
    "Липецк",
    "Магас",
    "Майкоп",
    "Махачкала",
    "Москва",
    "Мурманск",
    "Нальчик",
    "Нарьян-Мар",
    "Нижний Новгород",
    "Новосибирск",
    "Омск",
    "Орёл",
    "Оренбург",
    "Пенза",
    "Пермь",
    "Петрозаводск",
    "Петропавловск-Камчатский",
    "Псков",
    "Ростов-на-Дону",
    "Рязань",
    "Салехард",
    "Самара",
    "Санкт-Петербург",
    "Саранск",
    "Саратов",
    "Севастополь",
    "Симферополь",
    "Смоленск",
    "Ставрополь",
    "Сыктывкар",
    "Тамбов",
    "Тверь",
    "Томск",
    "Тула",
    "Тюмень",
    "Улан-Удэ",
    "Ульяновск",
    "Уфа",
    "Хабаровск",
    "Ханты-Мансийск",
    "Чебоксары",
    "Челябинск",
    "Черкесск",
    "Чита",
    "Элиста",
    "Южно-Сахалинск",
    "Якутск",
    "Ярославль",
)

_CITIES_LOWER = {city.lower(): city for city in REGIONAL_CENTERS_RU}

# Варианты названий из внешних API (EN / сокращения)
_CITY_ALIASES: dict[str, str] = {
    "moscow": "Москва",
    "saint petersburg": "Санкт-Петербург",
    "st petersburg": "Санкт-Петербург",
    "sankt-peterburg": "Санкт-Петербург",
    "nizhny novgorod": "Нижний Новгород",
    "nizhniy novgorod": "Нижний Новгород",
    "yekaterinburg": "Екатеринбург",
    "ekaterinburg": "Екатеринбург",
    "chelyabinsk": "Челябинск",
    "krasnodar": "Краснодар",
    "perm": "Пермь",
    "voronezh": "Воронеж",
    "samara": "Самара",
    "kazan": "Казань",
    "volgograd": "Волгоград",
    "novosibirsk": "Новосибирск",
    "rostov-on-don": "Ростов-на-Дону",
    "rostov on don": "Ростов-на-Дону",
    "saratov": "Саратов",
    "ufa": "Уфа",
    "krasnoyarsk": "Красноярск",
    "vladivostok": "Владивосток",
    "sevastopol": "Севастополь",
    "simferopol": "Симферополь",
}


def normalize_city_label(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if value.lower().startswith("г."):
        value = value[2:].strip()
    if value.lower().startswith("г "):
        value = value[1:].strip()
    return value


def match_city_name(raw: str) -> str | None:
    """Сопоставляет название из геолокации со списком городов магазина."""
    label = normalize_city_label(raw)
    if not label:
        return None

    direct = _CITIES_LOWER.get(label.lower())
    if direct:
        return direct

    alias = _CITY_ALIASES.get(label.lower())
    if alias:
        return alias

    lowered = label.lower()
    for city in REGIONAL_CENTERS_RU:
        if city.lower() in lowered or lowered in city.lower():
            return city

    return None


def get_client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        if ip:
            return ip
    return request.META.get("REMOTE_ADDR")


def _is_private_ip(ip: str) -> bool:
    if ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
        return True
    if ip.startswith("fe80:") or ip.startswith("fc") or ip.startswith("fd"):
        return True
    return False


def lookup_city_by_ip(
    ip: str,
    *,
    fetcher: Callable[[str], dict | None] | None = None,
) -> str:
    """Определяет город по IP; при ошибке — DEFAULT_CITY."""
    if not ip or _is_private_ip(ip):
        return DEFAULT_CITY

    payload = (fetcher or _fetch_geo_ip_api)(ip)
    if not payload:
        return DEFAULT_CITY

    country = (payload.get("countryCode") or "").upper()
    if country and country != "RU":
        return DEFAULT_CITY

    for key in ("city", "regionName"):
        matched = match_city_name(payload.get(key) or "")
        if matched:
            return matched

    return DEFAULT_CITY


def _fetch_geo_ip_api(ip: str) -> dict | None:
    url = (
        f"http://ip-api.com/json/{ip}"
        "?lang=ru&fields=status,message,countryCode,city,regionName"
    )
    try:
        with urllib.request.urlopen(url, timeout=2.5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    if data.get("status") != "success":
        return None
    return data
