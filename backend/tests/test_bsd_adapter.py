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
    assert fx.local_date == "2026年06月12日"
    assert fx.local_time == "03:00"


def test_event_to_internal_dict_teams():
    event = {
        "id": 9001,
        "home_team": {"id": 498, "name": "Colombia"},
        "away_team": {"id": 491, "name": "Portugal"},
        "home_team_id": 498,
        "away_team_id": 491,
        "status": "finished",
        "home_score": 2,
        "away_score": 1,
        "event_date": "2026-06-28T19:00:00+00:00",
        "round_name": "Round of 32",
    }
    fx = event_to_internal(event)
    assert fx.home_name == "哥伦比亚"
    assert fx.away_name == "葡萄牙"
    assert fx.status == "finished"


def test_event_bsd_team_ids():
    from app.ingest.bsd_adapter import event_bsd_team_ids

    ids = event_bsd_team_ids(
        {
            "home_team": {"id": 493, "name": "England"},
            "away_team": {"id": 494, "name": "Croatia"},
        }
    )
    assert ids == frozenset({493, 494})


def test_bsd_event_to_local_schedule():
    from app.ingest.bsd_adapter import bsd_event_to_local_schedule

    date_cn, time_cn, _ = bsd_event_to_local_schedule(
        {"event_date": "2026-06-24T17:00:00+00:00", "venue_name": "SoFi Stadium"}
    )
    assert date_cn == "2026年06月25日"
    assert time_cn == "01:00"


def test_knockout_placeholder():
    assert is_knockout_placeholder("W101") is True
    assert bsd_name_to_local("W101") is None


def test_team_pair_key():
    assert team_pair_key("墨西哥", "韩国") == team_pair_key("韩国", "墨西哥")
