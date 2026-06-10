"""Post-process agent reports for numeric consistency and live-mode accuracy."""

from __future__ import annotations

import re
from typing import Any


def normalize_win_probability(wp: dict[str, Any] | None) -> dict[str, float]:
    """Ensure win probabilities are non-negative and sum to 1."""
    if not wp:
        return {"team1": 0.33, "draw": 0.34, "team2": 0.33}

    t1 = max(0.0, float(wp.get("team1", 0.33)))
    draw = max(0.0, float(wp.get("draw", 0.34)))
    t2 = max(0.0, float(wp.get("team2", 0.33)))
    total = t1 + draw + t2
    if total <= 0:
        return {"team1": 0.33, "draw": 0.34, "team2": 0.33}
    return {"team1": t1 / total, "draw": draw / total, "team2": t2 / total}


def compute_live_fingerprint(live: dict | None) -> str:
    """Cache key fragment for live mode — changes when score/minute changes."""
    if not live or not live.get("found"):
        return "no_live"
    return f"{live.get('status')}|{live.get('score')}|{live.get('minute')}|{live.get('period')}"


def _parse_score(score_str: str | None) -> tuple[int, int] | None:
    if not score_str:
        return None
    match = re.match(r"^\s*(\d+)\s*:\s*(\d+)\s*$", str(score_str))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _apply_live_score_sanity(
    wp: dict[str, float],
    live: dict,
    team1: str,
    team2: str,
) -> tuple[dict[str, float], list[str]]:
    """Nudge win rates when live score strongly contradicts LLM output."""
    warnings: list[str] = []
    parsed = _parse_score(live.get("score"))
    if not parsed:
        return wp, warnings

    home, away = parsed
    minute = int(live.get("minute") or 0)
    if minute < 15:
        return wp, warnings

    diff = home - away
    if diff == 0:
        return wp, warnings

    leader_is_team1 = diff > 0
    leader_wp = wp["team1"] if leader_is_team1 else wp["team2"]
    leader_name = team1 if leader_is_team1 else team2
    margin = abs(diff)

    min_leader = 0.45 + min(margin * 0.08, 0.25) + min(minute / 120, 0.15)
    if leader_wp >= min_leader:
        return wp, warnings

    adjusted = dict(wp)
    boost = min_leader - leader_wp
    if leader_is_team1:
        adjusted["team1"] = min_leader
        pool = adjusted["draw"] + adjusted["team2"]
        if pool > 0:
            scale = (1.0 - min_leader) / pool
            adjusted["draw"] *= scale
            adjusted["team2"] *= scale
    else:
        adjusted["team2"] = min_leader
        pool = adjusted["draw"] + adjusted["team1"]
        if pool > 0:
            scale = (1.0 - min_leader) / pool
            adjusted["draw"] *= scale
            adjusted["team1"] *= scale

    warnings.append(
        f"已根据 live 比分 {live.get('score')}（{minute}'）校准胜率，"
        f"领先方 {leader_name} 原 {leader_wp:.0%} → {min_leader:.0%}"
    )
    return normalize_win_probability(adjusted), warnings


def validate_and_fix_report(
    raw: dict,
    facts: dict,
    mode: str,
    team1: str,
    team2: str,
) -> tuple[dict, list[str]]:
    """Normalize numeric fields and apply mode-specific sanity checks."""
    fixed = dict(raw)
    warnings: list[str] = []

    wp = normalize_win_probability(fixed.get("win_probability"))
    live = facts.get("live")
    if mode == "live" and live and live.get("found"):
        wp, live_warnings = _apply_live_score_sanity(wp, live, team1, team2)
        warnings.extend(live_warnings)
        fixed["_live_fingerprint"] = compute_live_fingerprint(live)
    fixed["win_probability"] = wp

    conf = float(fixed.get("confidence", 0.7))
    fixed["confidence"] = max(0.05, min(1.0, conf))

    injuries = facts.get("injuries") or {}
    has_injury_data = any((v.get("injuries") or []) for v in injuries.values() if isinstance(v, dict))
    injury_text = str(fixed.get("injury_impact") or "")
    if injury_text and not has_injury_data and any(k in injury_text for k in ("重伤", "缺阵", "伤病潮")):
        fixed["confidence"] = max(0.05, fixed["confidence"] - 0.12)
        warnings.append("伤病描述与数据库不一致，已下调置信度")

    if not facts.get("news"):
        nd = str(fixed.get("news_digest") or fixed.get("summary") or "")
        if nd and "新闻" in nd and "不足" not in nd and "暂无" not in nd:
            fixed["confidence"] = max(0.05, fixed["confidence"] - 0.08)
            warnings.append("无新闻数据但摘要引用了舆情，已下调置信度")

    return fixed, warnings
