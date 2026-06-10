"""Transform raw LLM agent output into fan-friendly, betting-oriented UI payloads."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.report_validator import normalize_win_probability

_JSON_LIKE = re.compile(r"^\s*[\[{]")
_ACTION_LABELS = {
    "get_team_profile": "球队资料",
    "get_injury_report": "伤病情况",
    "search_news": "新闻检索",
    "get_tactical_matchup": "战术对位",
    "summarize_news": "新闻摘要",
    "analyze_matchup": "战术分析",
    "synthesize": "综合报告",
    "validate": "事实核查",
    "skipped": "已跳过",
}


def _looks_like_json(text: str) -> bool:
    t = text.strip()
    return bool(_JSON_LIKE.match(t)) or ('":' in t and ("{" in t or "[" in t))


def sanitize_display_text(value: Any, max_len: int = 1200) -> str:
    """Coerce LLM output to plain Chinese-friendly text; never dump raw JSON to users."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in (
            "digest",
            "brief",
            "summary",
            "text",
            "message",
            "betting_notes",
            "advice",
            "betting_rationale",
            "one_line_verdict",
            "injury_impact",
            "tactical_edge",
            "scenario_analysis",
            "corrections",
            "notes",
        ):
            if key in value and value[key]:
                return sanitize_display_text(value[key], max_len)
        parts: list[str] = []
        for k, v in value.items():
            if k in ("sentiment", "approved", "confidence", "issues", "key_topics", "token_usage"):
                continue
            t = sanitize_display_text(v, 300)
            if t:
                parts.append(t)
        return "；".join(parts)[:max_len]
    if isinstance(value, list):
        parts = [sanitize_display_text(x, 300) for x in value]
        return "；".join(p for p in parts if p)[:max_len]

    s = str(value).strip()
    if not s or s in ("{}", "[]", "null", "None"):
        return ""
    if _looks_like_json(s):
        try:
            parsed = json.loads(s)
            return sanitize_display_text(parsed, max_len)
        except (json.JSONDecodeError, TypeError):
            s = re.sub(r'[{}\[\]"]', " ", s)
            s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len]


def normalize_string_list(items: Any, max_items: int = 6) -> list[str]:
    if not items:
        return []
    if isinstance(items, str):
        items = [items]
    out: list[str] = []
    for item in items:
        t = sanitize_display_text(item, 220)
        if t and t not in out:
            out.append(t)
    return out[:max_items]


def _infer_pick(wp: dict[str, float], team1: str, team2: str) -> dict[str, Any]:
    t1, draw, t2 = wp["team1"], wp["draw"], wp["team2"]
    options = [
        ("1", team1, t1),
        ("X", "平局", draw),
        ("2", team2, t2),
    ]
    pick_code, pick_name, prob = max(options, key=lambda x: x[2])
    label = f"{pick_name} 胜" if pick_code != "X" else "平局"
    if prob >= 0.52:
        tier = "较高"
    elif prob >= 0.42:
        tier = "中等"
    else:
        tier = "分散"
    return {
        "recommended_pick": pick_code,
        "pick_label": label,
        "pick_probability": round(prob, 3),
        "confidence_tier": tier,
    }


def build_betting_guide(raw: dict, team1: str, team2: str, mode: str) -> dict[str, Any]:
    wp = normalize_win_probability(raw.get("win_probability"))
    pick = _infer_pick(wp, team1, team2)

    predicted = sanitize_display_text(raw.get("predicted_score") or raw.get("score") or "-", 20)
    total_goals = sanitize_display_text(raw.get("total_goals_hint") or raw.get("total_goals") or "", 80)
    cards = sanitize_display_text(raw.get("card_penalty_hint") or raw.get("red_cards") or raw.get("penalties") or "", 80)

    rationale = sanitize_display_text(
        raw.get("betting_rationale") or raw.get("betting_notes") or raw.get("advice") or "",
        600,
    )
    verdict = sanitize_display_text(raw.get("one_line_verdict") or raw.get("summary") or "", 200)

    watch = normalize_string_list(raw.get("fan_watchpoints") or raw.get("watch_points") or raw.get("key_factors"), 5)
    risks = normalize_string_list(raw.get("key_risks") or raw.get("critic_issues") or [], 4)

    conf = float(raw.get("confidence", 0.7))
    if mode == "live":
        stake = "赛中变化快，建议小额娱乐或观望，勿追高。"
    elif conf >= 0.72 and pick["pick_probability"] >= 0.48:
        stake = "模型相对一致，可用免费竞猜或 10~30 币小额娱乐参考。"
    elif pick["confidence_tier"] == "分散":
        stake = "胜平负较分散，建议优先免费竞猜或降低质押。"
    else:
        stake = "仅供娱乐参考，建议小额质押并关注临场变化。"

    if not rationale and verdict:
        rationale = verdict

    return {
        **pick,
        "predicted_score": predicted,
        "total_goals_hint": total_goals or "暂无明确进球区间提示",
        "card_penalty_hint": cards or "暂无显著红黄牌/点球风险提示",
        "stake_suggestion": stake,
        "one_line_verdict": verdict or f"倾向 {pick['pick_label']}，预测比分 {predicted}",
        "rationale": rationale or f"综合胜率与战术/舆情，当前更倾向 {pick['pick_label']}。",
        "watch_points": watch,
        "key_risks": risks,
        "model_confidence": round(conf, 2),
        "win_probability": wp,
    }


def summarize_step(step: dict) -> dict[str, str]:
    agent = str(step.get("agent") or "")
    action = str(step.get("action") or "")
    output = step.get("output")

    if action == "skipped":
        reason = ""
        if isinstance(output, dict):
            reason = sanitize_display_text(output.get("reason"), 120)
        return {
            "agent": agent,
            "action": _ACTION_LABELS.get(action, action),
            "summary": reason or "本步骤已跳过",
        }

    summary = ""
    if isinstance(output, dict):
        if agent == "NewsAgent":
            summary = sanitize_display_text(output.get("digest"), 200)
            topics = normalize_string_list(output.get("key_topics"), 3)
            if topics:
                summary = (summary + " 焦点：" + "、".join(topics)).strip()
        elif agent == "TacticalAgent":
            summary = sanitize_display_text(output.get("brief"), 200)
        elif agent == "PredictAgent":
            summary = sanitize_display_text(output.get("summary") or output.get("one_line_verdict"), 200)
        elif agent == "CriticAgent":
            summary = sanitize_display_text(output.get("corrections"), 200)
            issues = normalize_string_list(output.get("issues"), 2)
            if issues:
                summary = (summary + " 注意：" + "；".join(issues)).strip()
        elif agent == "DataAgent":
            if "injury" in action.lower():
                summary = "已同步伤病名单"
            elif "news" in action.lower():
                summary = "已检索相关新闻"
            else:
                summary = "已采集球队基础数据"
        else:
            summary = sanitize_display_text(output, 180)
    else:
        summary = sanitize_display_text(output, 180)

    if not summary:
        summary = f"完成 {_ACTION_LABELS.get(action, action)}"

    return {
        "agent": agent,
        "action": _ACTION_LABELS.get(action, action),
        "summary": summary,
    }


def present_reasoning_trace(steps: list[dict]) -> list[dict[str, str]]:
    trace: list[dict[str, str]] = []
    for step in steps or []:
        if not step.get("agent"):
            continue
        trace.append(summarize_step(step))
    return trace


def present_user_report(
    raw: dict,
    steps: list[dict],
    team1: str,
    team2: str,
    mode: str = "pre_match",
) -> dict[str, Any]:
    """Build API/frontend-facing report: no raw JSON blobs in text fields."""
    wp = normalize_win_probability(raw.get("win_probability"))
    betting_guide = build_betting_guide(raw, team1, team2, mode)

    key_factors = normalize_string_list(raw.get("key_factors"))
    tactical = raw.get("tactical_brief") if isinstance(raw.get("tactical_brief"), dict) else {}

    return {
        "summary": sanitize_display_text(raw.get("summary"), 800),
        "predicted_score": betting_guide["predicted_score"],
        "win_probability": wp,
        "key_factors": key_factors,
        "injury_impact": sanitize_display_text(raw.get("injury_impact"), 500),
        "tactical_edge": sanitize_display_text(raw.get("tactical_edge") or tactical.get("brief"), 500),
        "betting_notes": betting_guide["rationale"],
        "confidence": float(raw.get("confidence", 0.7)),
        "sources": raw.get("sources") or [],
        "reasoning_trace": present_reasoning_trace(steps),
        "news_digest": sanitize_display_text(raw.get("news_digest") or raw.get("news_digest"), 600),
        "scenario_analysis": sanitize_display_text(raw.get("scenario_analysis"), 300),
        "critic_notes": sanitize_display_text(raw.get("critic_notes"), 400),
        "critic_issues": normalize_string_list(raw.get("critic_issues"), 5),
        "tactical_brief": {
            "brief": sanitize_display_text(tactical.get("brief") or raw.get("tactical_edge"), 400),
            "team1_edge": sanitize_display_text(tactical.get("team1_edge"), 200),
            "team2_edge": sanitize_display_text(tactical.get("team2_edge"), 200),
            "key_matchups": normalize_string_list(tactical.get("key_matchups"), 5),
        },
        "validation_warnings": normalize_string_list(raw.get("validation_warnings"), 8),
        "live_context": raw.get("_live_fingerprint"),
        "betting_guide": betting_guide,
        "watch_points": betting_guide.get("watch_points") or [],
        "mode": mode,
    }
