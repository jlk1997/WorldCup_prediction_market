"""Insight helper tests."""

from app.agents.insight_helpers import extract_betting_pick


def test_extract_betting_pick_from_win_probability():
    out = {
        "win_probability": {"team1": 0.55, "draw": 0.25, "team2": 0.2},
        "summary": "test",
    }
    pick, label = extract_betting_pick(out, "阿根廷", "法国")
    assert pick == "home"
    assert label
