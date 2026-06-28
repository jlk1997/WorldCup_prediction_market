"""Grant payload schema for cash shop products (mint_bundle, ai_pack, etc.)."""

from __future__ import annotations

from app.core.exceptions import BadRequestError

CASH_GRANT_PAYLOAD_SCHEMA = {
    "mint_event_id": "int — 打新活动 ID（mint_bundle 白名单资格）",
    "ai_live_credits": "int — AI live 分析次数包",
    "ai_refresh_credits": "int — AI 强制刷新次数包",
    "bonus_coins": "int — 额外球迷币（coins_grant 为 0 时生效）",
    "mint_coupon_note": "str — 运营备注（展示用）",
    "collection_pass_premium": "bool — 解锁藏品手册尊享轨道",
    "collection_pass_level_skip": "int — 手册直升等级",
    "avatar_frame": "str — 头像框标识",
    "theme_key": "str — 全站主题",
    "badge_code": "str — 徽章 code",
    "badge_title": "str — 徽章展示名",
}

_ALLOWED_KEYS = frozenset(CASH_GRANT_PAYLOAD_SCHEMA.keys())


def validate_cash_grant_payload(payload: dict | None, *, product_type: str | None = None) -> dict | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise BadRequestError("grant_payload 必须是 JSON 对象")
    unknown = set(payload.keys()) - _ALLOWED_KEYS
    if unknown:
        raise BadRequestError(f"grant_payload 含未知字段: {', '.join(sorted(unknown))}")
    if not payload:
        raise BadRequestError("grant_payload 至少包含一项权益")
    if mid := payload.get("mint_event_id"):
        try:
            n = int(mid)
        except (TypeError, ValueError) as exc:
            raise BadRequestError("mint_event_id 必须是正整数") from exc
        if n <= 0:
            raise BadRequestError("mint_event_id 必须是正整数")
        payload = {**payload, "mint_event_id": n}
    for key in ("ai_live_credits", "ai_refresh_credits", "bonus_coins"):
        val = payload.get(key)
        if val is None:
            continue
        try:
            n = int(val)
        except (TypeError, ValueError) as exc:
            raise BadRequestError(f"{key} 必须是正整数") from exc
        if n <= 0:
            raise BadRequestError(f"{key} 必须是正整数")
        payload[key] = n
    if product_type == "mint_bundle" and not payload.get("mint_event_id"):
        if not (payload.get("ai_live_credits") or payload.get("ai_refresh_credits")):
            raise BadRequestError("mint_bundle 需配置 mint_event_id 或 AI 额度")
    if payload.get("collection_pass_premium") is not None and not isinstance(
        payload.get("collection_pass_premium"), bool
    ):
        raise BadRequestError("collection_pass_premium 须为布尔值")
    if payload.get("badge_code") and not payload.get("badge_title"):
        raise BadRequestError("badge_code 需同时提供 badge_title")
    return payload
