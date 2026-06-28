from app.services.prediction_knowledge_service import snippet_for_teams


def test_snippet_for_teams_includes_team():
    text = snippet_for_teams("荷兰", "葡萄牙")
    assert "荷兰" in text or "葡萄牙" in text or "冠军" in text
