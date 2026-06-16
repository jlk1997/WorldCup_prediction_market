"""Tests for leaderboard reward config parsing."""

from app.core.leaderboard_rewards import parse_season_rank_rewards, season_settle_top_n


def test_parse_season_rank_rewards_range():
    raw = "1:500:300:120,4-6:100:50:0"
    m = parse_season_rank_rewards(raw)
    assert m[1] == (500, 300, 120)
    assert m[4] == (100, 50, 0)
    assert m[6] == (100, 50, 0)
    assert season_settle_top_n(m) == 6
