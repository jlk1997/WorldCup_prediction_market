"""卡牌对决战斗引擎 — BP、位置克制、回合结算。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from app.data.combat_stats import STAT_KEYS, normalize_position

STAR_MULT = {1: 1.0, 2: 1.12, 3: 1.25}
RARITY_MOD = {"common": 1.0, "rare": 1.02, "epic": 1.05, "legend": 1.08}

POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "FWD": {"shoot": 0.35, "pace": 0.25, "dribble": 0.25, "physical": 0.15},
    "MID": {"pass": 0.30, "dribble": 0.25, "defend": 0.20, "pace": 0.25},
    "DEF": {"defend": 0.40, "physical": 0.30, "pace": 0.20, "pass": 0.10},
    "GK": {"defend": 0.45, "physical": 0.30, "pace": 0.15, "pass": 0.10},
}

MATCHUP_TABLE: dict[tuple[str, str], tuple[float, str]] = {
    ("FWD", "DEF"): (0.92, "铁壁封堵"),
    ("FWD", "GK"): (0.92, "铁壁封堵"),
    ("FWD", "MID"): (1.05, "防线空档"),
    ("DEF", "FWD"): (1.08, "反击利器"),
    ("GK", "FWD"): (0.95, "门将封堵"),
}

STAT_LABELS = {
    "pace": "速度",
    "shoot": "射门",
    "pass": "传球",
    "dribble": "盘带",
    "defend": "防守",
    "physical": "力量",
}

NARRATIVE_TEMPLATES = {
    "pace": "{name} 速度压制，突破成功！",
    "shoot": "{name} 一脚世界波，门将无力回天！",
    "pass": "{name} 精妙传球撕破防线！",
    "dribble": "{name} 华丽盘带，防守球员被晃倒！",
    "defend": "{name} 铁壁防守，化解攻势！",
    "physical": "{name} 身体对抗占得上风！",
}


@dataclass
class CombatCard:
    """可来自用户持有卡或 AI 虚拟卡。"""

    name: str
    rarity: str
    image_url: str | None
    position: str
    star: int
    serial_no: int | None
    team_id: int | None
    stats: dict[str, int]
    overall_rating: int
    user_card_id: int | None = None
    card_code: str | None = None
    side: str = "challenger"
    chemistry_bonus_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        bp = battle_power(self)
        return {
            "user_card_id": self.user_card_id,
            "card_code": self.card_code,
            "name": self.name,
            "rarity": self.rarity,
            "image_url": self.image_url,
            "position": self.position,
            "star": self.star,
            "overall_rating": self.overall_rating,
            "stats": dict(self.stats),
            "bp": bp,
            "team_id": self.team_id,
        }


@dataclass
class RoundResult:
    round_no: int
    challenger_card: dict[str, Any]
    defender_card: dict[str, Any]
    challenger_score: float
    defender_score: float
    winner_side: str
    narrative: str
    stat_comparison: list[dict[str, Any]]
    modifiers: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round": self.round_no,
            "challenger_card": self.challenger_card,
            "defender_card": self.defender_card,
            "challenger_score": round(self.challenger_score, 2),
            "defender_score": round(self.defender_score, 2),
            "winner_side": self.winner_side,
            "narrative": self.narrative,
            "stat_comparison": self.stat_comparison,
            "modifiers": self.modifiers,
        }


def _serial_premium(serial_no: int | None) -> float:
    if not serial_no or serial_no > 10:
        return 0.0
    return (11 - serial_no) * 0.003


def weighted_stat_score(stats: dict[str, int], position: str) -> float:
    pos = normalize_position(position)
    weights = POSITION_WEIGHTS.get(pos, POSITION_WEIGHTS["MID"])
    total = 0.0
    for key, w in weights.items():
        total += float(stats.get(key, 50)) * w
    return total


def chemistry_bonus_pct(cards: list[CombatCard]) -> dict[int, float]:
    """按 card index 返回 chemistry 加成（同队 +3%，含传奇 +2%）。"""
    team_ids = [c.team_id for c in cards if c.team_id]
    same_team = len(set(team_ids)) == 1 and len(team_ids) == len(cards) and len(cards) > 1
    has_legend = any(c.rarity == "legend" for c in cards)
    bonus = 0.0
    if same_team:
        bonus += 0.03
    if has_legend:
        bonus += 0.02
    return {i: bonus for i in range(len(cards))}


def battle_power(card: CombatCard, *, rng_pct: float = 0.0) -> int:
    pos = normalize_position(card.position)
    base = weighted_stat_score(card.stats, pos)
    star_m = STAR_MULT.get(int(card.star or 1), 1.0)
    rarity_m = RARITY_MOD.get(card.rarity or "common", 1.0)
    serial_m = 1.0 + _serial_premium(card.serial_no)
    chem_m = 1.0 + card.chemistry_bonus_pct
    score = base * star_m * rarity_m * serial_m * chem_m * (1.0 + rng_pct)
    return max(1, int(round(score)))


def matchup_modifier(pos_a: str, pos_b: str) -> tuple[float, str]:
    a, b = normalize_position(pos_a), normalize_position(pos_b)
    if a == b:
        return 1.0, "正面对决"
    return MATCHUP_TABLE.get((a, b), (1.0, ""))


def _top_stat_diff(
    stats_a: dict[str, int], stats_b: dict[str, int], winner: str
) -> str:
    best_key = "pace"
    best_diff = -1
    for key in STAT_KEYS:
        diff = abs(stats_a.get(key, 50) - stats_b.get(key, 50))
        if diff > best_diff:
            best_diff = diff
            best_key = key
    return best_key


def generate_narrative(
    winner_card: CombatCard,
    loser_card: CombatCard,
    *,
    modifier_label: str = "",
) -> str:
    w_stats = winner_card.stats
    l_stats = loser_card.stats
    key = _top_stat_diff(w_stats, l_stats, winner_card.side)
    tpl = NARRATIVE_TEMPLATES.get(key, "{name} 占据上风！")
    text = tpl.format(name=winner_card.name)
    if modifier_label:
        text = f"「{modifier_label}」{text}"
    return text


def stat_comparison(
    card_a: CombatCard, card_b: CombatCard, weights: dict[str, float] | None = None
) -> list[dict[str, Any]]:
    keys = list(weights.keys()) if weights else list(STAT_KEYS)
    out = []
    for key in keys:
        a = card_a.stats.get(key, 50)
        b = card_b.stats.get(key, 50)
        winner = "a" if a > b else ("b" if b > a else "tie")
        out.append(
            {
                "key": key,
                "label": STAT_LABELS.get(key, key),
                "a": a,
                "b": b,
                "winner": winner,
            }
        )
    return out


def resolve_round(
    challenger: CombatCard,
    defender: CombatCard,
    round_no: int,
    *,
    rng_pct: float | None = None,
) -> RoundResult:
    if rng_pct is None:
        rng_pct = random.uniform(-0.03, 0.03)
    mod, mod_label = matchup_modifier(challenger.position, defender.position)
    c_score = battle_power(challenger, rng_pct=rng_pct) * mod
    d_score = battle_power(defender, rng_pct=-rng_pct)
    if mod_label and mod != 1.0:
        # matchup applied to challenger only
        pass
    winner = "challenger" if c_score >= d_score else "defender"
    winner_card = challenger if winner == "challenger" else defender
    loser_card = defender if winner == "challenger" else challenger
    pos = normalize_position(challenger.position)
    weights = POSITION_WEIGHTS.get(pos, POSITION_WEIGHTS["MID"])
    modifiers = []
    if mod_label and mod != 1.0:
        modifiers.append({"type": "matchup", "label": mod_label, "factor": mod})
    narrative = generate_narrative(winner_card, loser_card, modifier_label=mod_label)
    return RoundResult(
        round_no=round_no,
        challenger_card=challenger.to_dict(),
        defender_card=defender.to_dict(),
        challenger_score=c_score,
        defender_score=d_score,
        winner_side=winner,
        narrative=narrative,
        stat_comparison=stat_comparison(challenger, defender, weights),
        modifiers=modifiers,
    )


def resolve_duel(
    challenger_cards: list[CombatCard],
    defender_cards: list[CombatCard],
    *,
    mode: str = "best_of_3",
) -> dict[str, Any]:
    if len(challenger_cards) != 3 or len(defender_cards) != 3:
        raise ValueError("need exactly 3 cards per side")

    c_chem = chemistry_bonus_pct(challenger_cards)
    d_chem = chemistry_bonus_pct(defender_cards)
    for i, c in enumerate(challenger_cards):
        c.chemistry_bonus_pct = c_chem.get(i, 0.0)
    for i, dc in enumerate(defender_cards):
        dc.chemistry_bonus_pct = d_chem.get(i, 0.0)

    rounds: list[RoundResult] = []
    if mode == "total_power":
        c_total = sum(battle_power(c) for c in challenger_cards)
        d_total = sum(battle_power(c) for c in defender_cards)
        winner = "challenger" if c_total >= d_total else "defender"
        rounds.append(
            RoundResult(
                round_no=1,
                challenger_card={"name": "全队", "bp": c_total},
                defender_card={"name": "全队", "bp": d_total},
                challenger_score=float(c_total),
                defender_score=float(d_total),
                winner_side=winner,
                narrative="全队战力对决！",
                stat_comparison=[],
            )
        )
        c_wins = 1 if winner == "challenger" else 0
        d_wins = 1 if winner == "defender" else 0
    else:
        c_wins = d_wins = 0
        for rnd in range(3):
            if c_wins >= 2 or d_wins >= 2:
                break
            rr = resolve_round(challenger_cards[rnd], defender_cards[rnd], rnd + 1)
            rounds.append(rr)
            if rr.winner_side == "challenger":
                c_wins += 1
            else:
                d_wins += 1
        winner = "challenger" if c_wins >= d_wins else "defender"

    return {
        "mode": mode,
        "winner_side": winner,
        "challenger_round_wins": c_wins,
        "defender_round_wins": d_wins,
        "rounds": [r.to_dict() for r in rounds],
    }


def build_combat_card_from_row(
    row: Any,
    card: Any,
    *,
    side: str = "challenger",
    chemistry_bonus_pct: float = 0.0,
) -> CombatCard:
    attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
    stats_raw = attrs.get("combat_stats") if isinstance(attrs.get("combat_stats"), dict) else {}
    stats = {k: int(stats_raw.get(k, 50)) for k in STAT_KEYS}
    if all(v == 50 for v in stats.values()):
        from app.data.combat_stats import stats_from_player

        stats = stats_from_player(None, attrs.get("overall_rating"))
    return CombatCard(
        name=card.name,
        rarity=card.rarity or "common",
        image_url=card.image_url,
        position=normalize_position(attrs.get("position")),
        star=int(row.star or 1),
        serial_no=row.serial_no,
        team_id=card.team_id,
        stats=stats,
        overall_rating=int(attrs.get("overall_rating") or 70),
        user_card_id=row.id,
        card_code=card.code,
        side=side,
        chemistry_bonus_pct=chemistry_bonus_pct,
    )


def build_combat_card_from_virtual(v: dict[str, Any], *, side: str = "defender") -> CombatCard:
    stats_raw = v.get("stats") or v.get("combat_stats") or {}
    stats = {k: int(stats_raw.get(k, 50)) for k in STAT_KEYS}
    return CombatCard(
        name=str(v.get("name") or "AI 球员"),
        rarity=str(v.get("rarity") or "rare"),
        image_url=v.get("image_url"),
        position=normalize_position(v.get("position")),
        star=int(v.get("star") or 1),
        serial_no=v.get("serial_no"),
        team_id=v.get("team_id"),
        stats=stats,
        overall_rating=int(v.get("overall_rating") or 75),
        user_card_id=v.get("user_card_id"),
        card_code=v.get("card_code"),
        side=side,
    )


def deck_average_bp(cards: list[CombatCard]) -> float:
    if not cards:
        return 0.0
    return sum(battle_power(c) for c in cards) / len(cards)


def bp_tier(avg_bp: float) -> int:
    return max(0, int(avg_bp // 100))


def chemistry_labels(cards: list[CombatCard]) -> list[str]:
    labels: list[str] = []
    team_ids = [c.team_id for c in cards if c.team_id]
    if len(team_ids) == len(cards) and len(set(team_ids)) == 1 and len(cards) > 1:
        labels.append("同队化学反应 +3%")
    if any(c.rarity == "legend" for c in cards):
        labels.append("传奇光环 +2%")
    return labels


def deck_summary(cards: list[CombatCard]) -> dict[str, Any]:
    if not cards:
        return {
            "count": 0,
            "total_bp": 0,
            "avg_bp": 0,
            "tier": 0,
            "chemistry": [],
            "positions": [],
        }
    bps = [battle_power(c) for c in cards]
    chem = chemistry_labels(cards)
    bonus = 0.0
    if any("同队" in x for x in chem):
        bonus += 0.03
    if any("传奇" in x for x in chem):
        bonus += 0.02
    for i, c in enumerate(cards):
        c.chemistry_bonus_pct = bonus
    bps = [battle_power(c) for c in cards]
    avg = sum(bps) / len(bps)
    return {
        "count": len(cards),
        "total_bp": sum(bps),
        "avg_bp": int(round(avg)),
        "tier": bp_tier(avg),
        "chemistry": chem,
        "positions": [normalize_position(c.position) for c in cards],
        "cards": [c.to_dict() for c in cards],
    }


POSITION_LABELS = {"FWD": "前锋", "MID": "中场", "DEF": "后卫", "GK": "门将"}

MATCHUP_HINTS = [
    {"att": "FWD", "def": "DEF", "hint": "前锋打后卫略吃亏（铁壁封堵）"},
    {"att": "FWD", "def": "MID", "hint": "前锋打中场略占优（防线空档）"},
    {"att": "DEF", "def": "FWD", "hint": "后卫反击前锋略占优"},
]
