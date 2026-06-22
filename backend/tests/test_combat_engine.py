"""Combat engine unit tests."""

from app.services.combat_engine import (
    CombatCard,
    battle_power,
    build_combat_card_from_virtual,
    resolve_duel,
    resolve_round,
)


def _card(name: str, pos: str, stats: dict, **kw) -> CombatCard:
    base = {"pace": 70, "shoot": 70, "pass": 70, "dribble": 70, "defend": 70, "physical": 70}
    base.update(stats)
    return CombatCard(
        name=name,
        rarity=kw.get("rarity", "rare"),
        image_url=None,
        position=pos,
        star=kw.get("star", 1),
        serial_no=kw.get("serial_no"),
        team_id=kw.get("team_id"),
        stats=base,
        overall_rating=kw.get("overall_rating", 80),
    )


def test_battle_power_fwd_weights_shooting():
    fwd = _card("Striker", "FWD", {"shoot": 90, "pace": 80})
    bp = battle_power(fwd)
    assert bp > 70


def test_resolve_round_has_narrative():
    a = _card("A", "FWD", {"shoot": 88, "pace": 85})
    b = _card("B", "DEF", {"defend": 82, "physical": 80})
    rr = resolve_round(a, b, 1, rng_pct=0.0)
    assert rr.winner_side in ("challenger", "defender")
    assert rr.narrative
    assert len(rr.stat_comparison) >= 1


def test_resolve_duel_best_of_3():
    c = [_card(f"C{i}", "MID", {"pass": 75 + i}) for i in range(3)]
    d = [_card(f"D{i}", "MID", {"pass": 70 + i}) for i in range(3)]
    result = resolve_duel(c, d, mode="best_of_3")
    assert 2 <= len(result["rounds"]) <= 3
    assert result["winner_side"] in ("challenger", "defender")
    rw = result["challenger_round_wins"] + result["defender_round_wins"]
    assert rw == len(result["rounds"])
    assert max(result["challenger_round_wins"], result["defender_round_wins"]) >= 2


def test_resolve_duel_best_of_3_stops_at_two_wins():
    """Strong side should not play a third round after 2-0."""
    c = [_card(f"C{i}", "FWD", {"shoot": 99, "pace": 99}) for i in range(3)]
    d = [_card(f"D{i}", "DEF", {"defend": 40, "physical": 40}) for i in range(3)]
    result = resolve_duel(c, d, mode="best_of_3")
    assert len(result["rounds"]) == 2
    assert result["challenger_round_wins"] == 2


def test_ai_virtual_card_bp():
    v = build_combat_card_from_virtual(
        {
            "name": "AI",
            "position": "FWD",
            "stats": {"shoot": 85, "pace": 80, "pass": 70, "dribble": 75, "defend": 40, "physical": 70},
            "overall_rating": 82,
        }
    )
    assert battle_power(v) >= 50
