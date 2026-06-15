"""Tests for match score settlement helpers."""

from app.core.match_scores import result_pick_from_team_scores


def test_result_pick_requires_both_scores():
    assert result_pick_from_team_scores(2, None) is None
    assert result_pick_from_team_scores(None, 1) is None
    assert result_pick_from_team_scores(None, None) is None


def test_result_pick_normal():
    assert result_pick_from_team_scores(2, 0) == "home"
    assert result_pick_from_team_scores(0, 2) == "away"
    assert result_pick_from_team_scores(1, 1) == "draw"
