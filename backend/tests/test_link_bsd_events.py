"""Tests for BSD event linking logic."""

from app.db.models import Match
from app.ingest.bsd_link_service import _match_group_stage, _match_knockout, _group_events_by_round


def test_match_group_stage_by_team_pair():
    local = Match(
        id=1,
        group_name="A组",
        team1_name="墨西哥",
        team2_name="南非",
        round_type="group",
    )
    events = [
        {
            "id": 8287,
            "group_name": "Group A",
            "home_team": "Mexico",
            "away_team": "South Africa",
            "event_date": "2026-06-11T19:00:00+00:00",
        }
    ]
    hit = _match_group_stage(local, events)
    assert hit is not None
    assert hit["id"] == 8287


def test_match_knockout_by_bracket_order():
    local = Match(
        id=2,
        bracket_round="r32",
        bracket_order=1,
        round_type="knockout",
        team1_name="待定",
        team2_name="待定",
    )
    round_events = _group_events_by_round([
        {"id": 100, "round_name": "Round of 32", "event_date": "2026-07-06T03:00:00+00:00"},
        {"id": 101, "round_name": "Round of 32", "event_date": "2026-07-06T07:00:00+00:00"},
    ])
    hit = _match_knockout(local, round_events)
    assert hit is not None
    assert hit["id"] == 100
