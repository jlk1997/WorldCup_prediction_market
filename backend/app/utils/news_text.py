"""Clean RSS/HTML news summaries for display."""

from __future__ import annotations

import html
import re

_IMG_SRC = re.compile(
    r"""src=["'](https?://[^"']+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^"']*)?)["']""",
    re.IGNORECASE,
)
_BARE_IMG_URL = re.compile(
    r"""https?://\S+\.(?:jpg|jpeg|png|webp|gif)(?:\?\S*)?""",
    re.IGNORECASE,
)
_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+")


def clean_news_summary(text: str | None, *, max_len: int = 220) -> str:
    if not text:
        return ""
    raw = html.unescape(text.strip())
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    # Prefer img alt text when present
    raw = re.sub(
        r"""<img[^>]+alt=["']([^"']+)["'][^>]*>""",
        r" \1 ",
        raw,
        flags=re.IGNORECASE,
    )
    raw = _TAG.sub(" ", raw)
    raw = _URL.sub(" ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > max_len:
        raw = raw[: max_len - 1].rstrip() + "…"
    return raw


def extract_news_thumbnail(text: str | None) -> str | None:
    if not text:
        return None
    raw = html.unescape(text)
    m = _IMG_SRC.search(raw)
    if m:
        return m.group(1)
    m = _BARE_IMG_URL.search(raw)
    return m.group(0) if m else None
