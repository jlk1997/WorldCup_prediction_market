"""Tests for predict notification payload parsing."""

from app.core.predict_notify_parse import enrich_predict_payload, parse_teams_from_body


def test_parse_teams_from_body():
    t1, t2 = parse_teams_from_body("韩国 vs 捷克 比分 2:1 · 猜对 +30 累计积分")
    assert t1 == "韩国"
    assert t2 == "捷克"


def test_enrich_predict_payload_from_body():
    payload = enrich_predict_payload(
        {"status": "won"},
        "韩国 vs 捷克 比分 2:1 · 猜对 +30 累计积分",
    )
    assert payload["team1"] == "韩国"
    assert payload["team2"] == "捷克"
    assert payload["final_score"] == "2:1"
    assert payload["match_label"] == "韩国 vs 捷克"
