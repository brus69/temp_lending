from __future__ import annotations

import re

import bleach

ALLOWED_TAGS = [
    "p",
    "br",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "a",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "blockquote",
    "figure",
    "figcaption",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "span",
    "div",
    "hr",
]

ALLOWED_ATTRIBUTES = {
    "*": ["class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]

_DANGEROUS_BLOCK_RE = re.compile(
    r"<(script|style|iframe)\b[^<]*(?:(?!</\1>)<[^<]*)*</\1>",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_html(html: str) -> str:
    if not html:
        return ""
    html = _DANGEROUS_BLOCK_RE.sub("", html)
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
