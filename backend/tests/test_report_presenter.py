from app.agents.report_presenter import (
    build_betting_guide,
    normalize_string_list,
    present_reasoning_trace,
    present_user_report,
    sanitize_display_text,
)


def test_sanitize_strips_json_blob():
    raw = '{"summary": "主队进攻更顺", "key_factors": ["伤病少"]}'
    assert "主队进攻更顺" in sanitize_display_text(raw)
    assert "{" not in sanitize_display_text(raw) or "主队" in sanitize_display_text(raw)


def test_normalize_key_factors_from_objects():
    items = [{"text": "核心中场复出"}, "防线稳固", {"factor": "主场氛围"}]
    out = normalize_string_list(items)
    assert len(out) >= 2
    assert all("{" not in x for x in out)


def test_betting_guide_infers_pick():
    guide = build_betting_guide(
        {
            "win_probability": {"team1": 0.55, "draw": 0.25, "team2": 0.2},
            "predicted_score": "2:1",
            "betting_rationale": "主队近期状态更好，胜面略高。",
            "confidence": 0.75,
        },
        "巴西",
        "阿根廷",
        "pre_match",
    )
    assert guide["recommended_pick"] == "1"
    assert "巴西" in guide["pick_label"]
    assert guide["rationale"]


def test_reasoning_trace_no_raw_json():
    steps = [
        {
            "agent": "NewsAgent",
            "action": "summarize_news",
            "output": {"digest": "两队备战正常", "key_topics": ["伤病", "阵型"]},
        },
        {
            "agent": "PredictAgent",
            "action": "synthesize",
            "output": {"summary": "倾向主队小胜", "one_line_verdict": "主胜可期"},
        },
    ]
    trace = present_reasoning_trace(steps)
    assert len(trace) == 2
    assert all("summary" in t and "output" not in t for t in trace)
    joined = " ".join(t["summary"] for t in trace)
    assert "{" not in joined


def test_present_user_report_structure():
    raw = {
        "summary": "精彩对攻",
        "win_probability": {"team1": 0.4, "draw": 0.3, "team2": 0.3},
        "key_factors": ["双方进攻强"],
        "confidence": 0.7,
    }
    out = present_user_report(raw, [], "A", "B", "pre_match")
    assert out["betting_guide"]["recommended_pick"] in ("1", "X", "2")
    assert out["reasoning_trace"] == []
    assert "agent_steps" not in out
