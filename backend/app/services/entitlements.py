"""Human-readable entitlement summaries for products and orders."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.models.commerce import Product

_FRAME_LABELS = {
    "gold_wc": "头像金框",
    "silver_wc": "头像银框",
    "referral_squad": "召友头像框",
    "pass_silver": "手册银框",
}

_THEME_LABELS = {
    "team_spirit": "全站主题色",
    "gold_wc": "世界杯金主题",
    "pass_gold": "手册金主题",
}


def avatar_frame_label(frame: str | None) -> str | None:
    if not frame:
        return None
    return _FRAME_LABELS.get(frame, "专属头像框")


def theme_key_label(key: str | None) -> str | None:
    if not key:
        return None
    return _THEME_LABELS.get(key, "全站主题")


def season_pass_benefit_lines(settings: Settings | None = None) -> list[str]:
    s = settings or get_settings()
    return [
        "竞猜累计积分 1.2 倍",
        f"每日 +{s.season_pass_daily_coins} 球迷币",
        f"每日额外 {s.season_pass_extra_ai_free} 次免费 AI 分析",
    ]


def build_product_grant_summary(product: Product, settings: Settings | None = None) -> list[str]:
    s = settings or get_settings()
    lines: list[str] = []
    if product.coins_grant > 0:
        lines.append(f"+{product.coins_grant} 球迷币")
    if product.grant_season_pass_days > 0:
        lines.append(f"赛季通行证 {product.grant_season_pass_days} 天")
        lines.extend(season_pass_benefit_lines(s))
    payload = product.grant_payload or {}
    if not payload and product.sku == "team_cosmetic":
        payload = {"avatar_frame": "gold_wc", "theme_key": "team_spirit"}
    if frame := payload.get("avatar_frame"):
        label = avatar_frame_label(str(frame))
        if label:
            lines.append(label)
    if theme := payload.get("theme_key"):
        label = theme_key_label(str(theme))
        if label:
            lines.append(label)
    if extra := payload.get("extra_free_predict_daily"):
        lines.append(f"每日免费竞猜 +{int(extra)}")
    if payload.get("collection_pass_premium"):
        lines.extend(["解锁尊享手册轨道", "限定球星卡 · 确定性奖励（非盲盒）"])
    if product.product_type == "mint_event":
        lines.extend(["限量球星卡首发", "支付成功后分配序列号", "链上铸造异步完成"])
    if product.product_type == "mint_bundle":
        if payload.get("mint_event_id"):
            note = payload.get("mint_coupon_note") or "指定打新白名单资格"
            lines.append(str(note))
        if payload.get("ai_live_credits"):
            lines.append(f"AI 深度分析 ×{int(payload['ai_live_credits'])}")
        if payload.get("ai_refresh_credits"):
            lines.append(f"AI 强制刷新 ×{int(payload['ai_refresh_credits'])}")
        if payload.get("bonus_coins"):
            lines.append(f"+{int(payload['bonus_coins'])} 球迷币")
    if product.product_type == "season_ultimate":
        lines.extend(season_pass_benefit_lines(s))
        lines.extend(["解锁尊享手册轨道", "手册直升 +5 级", "头像金框", "全站主题色"])
        if badge_title := payload.get("badge_title"):
            lines.append(f"徽章「{badge_title}」")
    if payload.get("collection_pass_level_skip"):
        lines.append(f"手册直升 +{int(payload['collection_pass_level_skip'])} 级")
    if badge_title := payload.get("badge_title"):
        lines.append(f"徽章「{badge_title}」")
    elif product.product_type == "cosmetic" and not payload:
        lines.extend(["头像金框", "全站主题色"])
    return lines


def has_active_season_pass(user) -> bool:
    from datetime import datetime, timezone

    from app.services.ai_billing_service import _has_active_pass

    return _has_active_pass(user, datetime.now(timezone.utc).replace(tzinfo=None))
