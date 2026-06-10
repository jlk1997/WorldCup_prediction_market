"""Tests for team1/team2 score normalization."""

from app.core.match_scores import result_pick_from_team_scores, scores_for_team1_team2


def test_scores_aligned_when_bsd_home_is_team1():
    t1, t2 = scores_for_team1_team2("墨西哥", "南非", "墨西哥", "南非", 2, 1)
    assert (t1, t2) == (2, 1)


def test_scores_swapped_when_bsd_home_is_team2():
    t1, t2 = scores_for_team1_team2("墨西哥", "南非", "南非", "墨西哥", 1, 2)
    assert (t1, t2) == (2, 1)


def test_result_pick_team1_win():
    assert result_pick_from_team_scores(3, 1) == "home"
    assert result_pick_from_team_scores(0, 2) == "away"
    assert result_pick_from_team_scores(1, 1) == "draw"


def test_result_pick_missing_scores():
    assert result_pick_from_team_scores(None, None) is None
