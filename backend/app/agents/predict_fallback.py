"""PredictAgent 降级报告：LLM 不可用或 JSON 解析失败时基于事实包生成简版参考。"""

from __future__ import annotations

from typing import Any


def _fifa_rank(team: dict | None) -> int:
    if not team:
        return 80
    try:
        return max(1, int(team.get("fifa_ranking") or 80))
    except (TypeError, ValueError):
        return 80


def _win_probs_from_rank(r1: int, r2: int) -> dict[str, float]:
    s1 = 1.0 / r1
    s2 = 1.0 / r2
    draw = 0.28
    total = s1 + s2 + draw
    return {"team1": s1 / total, "draw": draw / total, "team2": s2 / total}


def _score_guess(wp: dict[str, float]) -> str:
    if wp["team1"] >= wp["team2"] and wp["team1"] >= wp["draw"]:
        return "2:1"
    if wp["team2"] >= wp["team1"] and wp["team2"] >= wp["draw"]:
        return "1:2"
    return "1:1"


def _pick_1x2(wp: dict[str, float]) -> str:
    if wp["team1"] >= wp["draw"] and wp["team1"] >= wp["team2"]:
        return "1"
    if wp["team2"] >= wp["draw"] and wp["team2"] >= wp["team1"]:
        return "2"
    return "X"


def build_fallback_predict_raw(
    team1: str,
    team2: str,
    context: dict[str, Any],
    mode: str,
    *,
    reason: str = "",
) -> dict[str, Any]:
    t1 = context.get("team1") if isinstance(context.get("team1"), dict) else {}
    t2 = context.get("team2") if isinstance(context.get("team2"), dict) else {}
    r1, r2 = _fifa_rank(t1), _fifa_rank(t2)
    wp = _win_probs_from_rank(r1, r2)
    news = context.get("news_digest") if isinstance(context.get("news_digest"), dict) else {}
    tactical = context.get("tactical_brief") if isinstance(context.get("tactical_brief"), dict) else {}
    digest = str(news.get("digest") or "").strip()
    tac_brief = str(tactical.get("brief") or "").strip()

    stronger = team1 if r1 < r2 else team2 if r2 < r1 else "双方"
    summary = (
        f"{team1}（FIFA #{r1}）对阵 {team2}（FIFA #{r2}）。"
        f"排名层面{'主队' if r1 < r2 else '客队' if r2 < r1 else '双方'}略占上风。"
    )
    if digest:
        summary = f"{summary} {digest[:120]}"

    factors = [
        f"FIFA 排名：{team1} #{r1} vs {team2} #{r2}",
        f"阵型：{t1.get('formation') or '—'} vs {t2.get('formation') or '—'}",
    ]
    if tac_brief:
        factors.append(tac_brief[:80])

    pick = _pick_1x2(wp)
    return {
        "summary": summary,
        "predicted_score": _score_guess(wp),
        "win_probability": wp,
        "key_factors": factors[:5],
        "injury_impact": "暂无可靠伤病数据影响判断。",
        "tactical_edge": tac_brief or f"{stronger} 在排名与账面实力上略优。",
        "betting_pick": pick,
        "betting_rationale": (
            f"基于 FIFA 排名与已知阵型的简版参考，倾向赛果 {pick}。"
            "AI 深度模型暂不可用，结论置信度较低，建议结合最新首发与临场再判断。"
        ),
        "one_line_verdict": f"排名略优方：{stronger}（简版参考）",
        "fan_watchpoints": [
            "此为简版参考，非完整 AI 报告",
            "关注赛前首发与伤病名单",
            "竞猜请控制仓位，勿过度依赖单一指标",
        ],
        "key_risks": ["AI 主模型未返回有效 JSON", "缺少最新新闻舆情" if not digest else "新闻样本有限"],
        "total_goals_hint": "参考中等进球区间",
        "card_penalty_hint": "数据不足，暂不做红黄牌倾向判断",
        "confidence": 0.42,
        "scenario_analysis": "若排名较低一方早进球，比赛可能转向开放对攻。",
        "_degraded": True,
        "_degraded_reason": reason[:200] if reason else "llm_unavailable",
        "mode_hint": mode,
    }
