from app.agents.report_validator import (
    compute_live_fingerprint,
    normalize_win_probability,
    validate_and_fix_report,
)


def test_normalize_win_probability_sums_to_one():
    wp = normalize_win_probability({"team1": 0.5, "draw": 0.3, "team2": 0.1})
    total = wp["team1"] + wp["draw"] + wp["team2"]
    assert abs(total - 1.0) < 0.001


def test_normalize_win_probability_handles_zeros():
    wp = normalize_win_probability({"team1": 0, "draw": 0, "team2": 0})
    total = wp["team1"] + wp["draw"] + wp["team2"]
    assert abs(total - 1.0) < 0.001


def test_live_fingerprint_changes_with_score():
    fp1 = compute_live_fingerprint({"found": True, "status": "live", "score": "1:0", "minute": 30})
    fp2 = compute_live_fingerprint({"found": True, "status": "live", "score": "2:0", "minute": 45})
    assert fp1 != fp2


def test_live_score_sanity_boosts_leader():
    facts = {
        "live": {"found": True, "score": "2:0", "minute": 70, "status": "live"},
        "injuries": {"A": {"injuries": []}, "B": {"injuries": []}},
        "news": [],
    }
    raw = {
        "win_probability": {"team1": 0.2, "draw": 0.3, "team2": 0.5},
        "confidence": 0.8,
    }
    fixed, warnings = validate_and_fix_report(raw, facts, "live", "A", "B")
    assert fixed["win_probability"]["team1"] > 0.45
    assert warnings
