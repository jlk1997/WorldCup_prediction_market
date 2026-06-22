"""PredictAgent 降级报告测试。"""

from app.agents.predict_fallback import build_fallback_predict_raw


def test_fallback_win_probability_sums_to_one():
    ctx = {
        "mode": "pre_match",
        "team1": {"name": "哥伦比亚", "fifa_ranking": 12, "formation": "4-3-3"},
        "team2": {"name": "刚果（金）", "fifa_ranking": 67, "formation": "4-3-3"},
        "news_digest": {"digest": "暂无新闻"},
        "tactical_brief": {},
    }
    raw = build_fallback_predict_raw("哥伦比亚", "刚果（金）", ctx, "pre_match", reason="test")
    wp = raw["win_probability"]
    assert abs(wp["team1"] + wp["draw"] + wp["team2"] - 1.0) < 0.001
    assert raw["_degraded"] is True
    assert raw["betting_pick"] in ("1", "X", "2")
    assert raw["confidence"] < 0.5
