"""Grant payload schema for redeem shop products."""

from __future__ import annotations

from app.core.exceptions import BadRequestError

GRANT_PAYLOAD_SCHEMA = {
    "avatar_frame": "str — 头像框标识，如 gold_wc",
    "theme_key": "str — 全站主题，如 team_spirit",
    "extra_free_predict_daily": "int — 累加每日额外免费竞猜次数",
    "badge_code": "str — 徽章 code",
    "badge_title": "str — 徽章展示名",
}

_ALLOWED_KEYS = frozenset(GRANT_PAYLOAD_SCHEMA.keys())


def validate_grant_payload(payload: dict | None) -> dict | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise BadRequestError("grant_payload 必须是 JSON 对象")
    unknown = set(payload.keys()) - _ALLOWED_KEYS
    if unknown:
        raise BadRequestError(f"grant_payload 含未知字段: {', '.join(sorted(unknown))}")
    if not payload:
        raise BadRequestError("grant_payload 至少包含一项权益")
    if payload.get("badge_code") and not payload.get("badge_title"):
        raise BadRequestError("badge_code 需同时提供 badge_title")
    extra = payload.get("extra_free_predict_daily")
    if extra is not None:
        try:
            n = int(extra)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("extra_free_predict_daily 必须是正整数") from exc
        if n <= 0:
            raise BadRequestError("extra_free_predict_daily 必须是正整数")
    for key in ("avatar_frame", "theme_key", "badge_code", "badge_title"):
        val = payload.get(key)
        if val is not None and not str(val).strip():
            raise BadRequestError(f"{key} 不能为空")
    return payload
