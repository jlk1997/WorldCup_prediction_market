"""Tests for BSD adapter."""

from app.ingest.bsd_adapter import event_to_internal, map_bsd_status, team_pair_key
from app.data.bsd_team_names import bsd_name_to_local, is_knockout_placeholder


def test_map_bsd_status():
    assert map_bsd_status("notstarted") == "scheduled"
    assert map_bsd_status("inprogress") == "live"
    assert map_bsd_status("finished") == "finished"


def test_resolve_event_status_infers_finished():
    from app.ingest.bsd_adapter import resolve_event_status

    assert resolve_event_status({"status": "notstarted", "current_minute": 90, "home_score": 1, "away_score": 0}) == "finished"


def test_event_to_internal_group_match():
    event = {
        "id": 8287,
        "home_team": "Mexico",
        "away_team": "South Africa",
        "status": "notstarted",
        "home_score": None,
        "away_score": None,
        "current_minute": None,
        "period": "",
        "group_name": "Group A",
        "round_name": None,
        "round_number": None,
        "event_date": "2026-06-11T19:00:00+00:00",
    }
    fx = event_to_internal(event)
    assert fx.external_id == 8287
    assert fx.home_name == "墨西哥"
    assert fx.away_name == "南非"
    assert fx.status == "scheduled"


def test_knockout_placeholder():
    assert is_knockout_placeholder("W101") is True
    assert bsd_name_to_local("W101") is None


def test_team_pair_key():
    assert team_pair_key("墨西哥", "韩国") == team_pair_key("韩国", "墨西哥")
