"""Signed tokens for public share pages (fan card, etc.)."""

from __future__ import annotations

import hashlib
import hmac


def _sign(secret: str, message: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16]


def make_card_share_token(user_id: int, secret: str) -> str:
    return f"{user_id}.{_sign(secret, f'card:{user_id}')}"


def parse_card_share_token(token: str, secret: str) -> int | None:
    token = (token or "").strip()
    if "." not in token:
        return None
    user_part, sig = token.rsplit(".", 1)
    if not user_part.isdigit() or not sig:
        return None
    user_id = int(user_part)
    expected = _sign(secret, f"card:{user_id}")
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id


def mask_nickname(nickname: str | None) -> str:
    name = (nickname or "球迷").strip() or "球迷"
    if len(name) <= 1:
        return f"{name}*"
    return f"{name[0]}**"
