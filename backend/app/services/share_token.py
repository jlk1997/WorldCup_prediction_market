"""Signed tokens for public share pages (fan card, collectible, etc.)."""

from __future__ import annotations

import base64
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


def _encode_card_code(card_code: str) -> str:
    return base64.urlsafe_b64encode(card_code.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_card_code(encoded: str) -> str | None:
    if not encoded:
        return None
    pad = "=" * (-len(encoded) % 4)
    try:
        return base64.urlsafe_b64decode(encoded + pad).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def make_collectible_share_token(user_id: int, card_code: str, secret: str) -> str:
    code_part = _encode_card_code(card_code)
    sig = _sign(secret, f"collectible:{user_id}:{card_code}")
    return f"{user_id}.{code_part}.{sig}"


def parse_collectible_share_token(token: str, secret: str) -> tuple[int, str] | None:
    token = (token or "").strip()
    parts = token.split(".")
    if len(parts) != 3:
        return None
    user_part, code_part, sig = parts
    if not user_part.isdigit() or not sig:
        return None
    card_code = _decode_card_code(code_part)
    if not card_code:
        return None
    user_id = int(user_part)
    expected = _sign(secret, f"collectible:{user_id}:{card_code}")
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id, card_code
