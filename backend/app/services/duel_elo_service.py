"""卡牌对决 ELO 与智能组牌。"""

from __future__ import annotations

import itertools
from typing import Any

from app.services.combat_engine import CombatCard, battle_power, deck_summary

DEFAULT_ELO = 1000
K_FACTOR_PVP = 32
K_FACTOR_AI = 8


def expected_score(elo_a: int, elo_b: int) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def elo_delta(winner_elo: int, loser_elo: int, *, k: int = K_FACTOR_PVP) -> tuple[int, int]:
    """返回 (winner_delta, loser_delta)。"""
    exp_w = expected_score(winner_elo, loser_elo)
    win_d = int(round(k * (1.0 - exp_w)))
    lose_d = int(round(k * (0.0 - (1.0 - exp_w))))
    return max(1, win_d), min(-1, lose_d)


def apply_pvp_elo(
    challenger_elo: int,
    defender_elo: int,
    winner_id: int,
    challenger_id: int,
    defender_id: int,
) -> dict[str, int]:
    if winner_id == challenger_id:
        w_elo, l_elo = challenger_elo, defender_elo
    else:
        w_elo, l_elo = defender_elo, challenger_elo
    win_d, lose_d = elo_delta(w_elo, l_elo)
    if winner_id == challenger_id:
        return {"challenger_delta": win_d, "defender_delta": lose_d}
    return {"challenger_delta": lose_d, "defender_delta": win_d}


def apply_ai_elo(player_elo: int, ai_elo: int, player_won: bool) -> int:
    """AI 练习模式小幅 ELO 波动。"""
    if player_won:
        win_d, _ = elo_delta(player_elo, ai_elo, k=K_FACTOR_AI)
        return win_d
    _, lose_d = elo_delta(ai_elo, player_elo, k=K_FACTOR_AI)
    return lose_d


def _deck_score(summary: dict[str, Any]) -> float:
    chem_bonus = len(summary.get("chemistry") or []) * 80
    positions = summary.get("positions") or []
    pos_bonus = len(set(positions)) * 15 if len(positions) == 3 else 0
    return float(summary.get("total_bp") or 0) + chem_bonus + pos_bonus


def recommend_deck_from_cards(cards: list[CombatCard], *, max_pool: int = 12) -> dict[str, Any]:
    """从可用卡中推荐最优 3 张组合。"""
    if len(cards) < 3:
        raise ValueError("need at least 3 cards")
    ranked = sorted(cards, key=lambda c: battle_power(c), reverse=True)[:max_pool]
    best_ids: list[int | None] = []
    best_score = -1.0
    best_summary: dict[str, Any] = {}
    for combo in itertools.combinations(ranked, 3):
        summary = deck_summary(list(combo))
        score = _deck_score(summary)
        if score > best_score:
            best_score = score
            best_summary = summary
            best_ids = [c.user_card_id for c in combo]
    return {
        "card_ids": [i for i in best_ids if i],
        "score": int(best_score),
        **best_summary,
        "reason": _recommend_reason(best_summary),
    }


def _recommend_reason(summary: dict[str, Any]) -> str:
    parts = [f"综合战力 {summary.get('avg_bp', 0)}"]
    chem = summary.get("chemistry") or []
    if chem:
        parts.append("触发" + "、".join(chem))
    positions = summary.get("positions") or []
    if len(set(positions)) >= 2:
        parts.append("位置搭配均衡")
    return "；".join(parts)


def elo_tier(elo: int) -> dict[str, str]:
    if elo >= 1400:
        return {"code": "grandmaster", "label": "大师"}
    if elo >= 1300:
        return {"code": "diamond", "label": "钻石"}
    if elo >= 1200:
        return {"code": "gold", "label": "黄金"}
    if elo >= 1100:
        return {"code": "silver", "label": "白银"}
    return {"code": "bronze", "label": "青铜"}
