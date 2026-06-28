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


def test_apply_bsd_schedule_updates_teams():
    from app.ingest.bsd_link_service import apply_bsd_schedule_to_match

    match = Match(
        id=20,
        bracket_round="r32",
        bracket_order=7,
        team1_name="西班牙",
        team2_name="佛得角",
        match_date="2026年07月02日",
        match_time="00:00",
    )
    event = {
        "id": 8370,
        "home_team": {"id": 475, "name": "Spain"},
        "away_team": {"id": 483, "name": "Austria"},
        "event_date": "2026-07-03T03:00:00+00:00",
        "status": "notstarted",
    }
    assert apply_bsd_schedule_to_match(match, event) is True
    assert match.team1_name == "西班牙"
    assert match.team2_name == "奥地利"
    assert match.match_date == "2026年07月03日"


def test_knockout_slot_by_bracket_order():
    from app.ingest.bsd_link_service import _bsd_event_for_knockout_slot, _group_events_by_round

    local = Match(bracket_round="r32", bracket_order=2)
    round_events = _group_events_by_round([
        {"id": 100, "round_name": "Round of 32", "event_date": "2026-07-01T01:00:00+00:00"},
        {"id": 101, "round_name": "Round of 32", "event_date": "2026-07-01T05:00:00+00:00"},
        {"id": 102, "round_name": "Round of 32", "event_date": "2026-07-01T09:00:00+00:00"},
    ])
    hit = _bsd_event_for_knockout_slot(local, round_events)
    assert hit is not None
    assert hit["id"] == 101


def test_apply_schedule_from_bsd():
    from app.ingest.bsd_link_service import apply_bsd_schedule_to_match

    match = Match(
        id=10,
        team1_name="韩国",
        team2_name="南非",
        match_date="2026年06月13日",
        match_time="14:00",
        stadium="洛杉矶 · SoFi体育场",
        external_fixture_id=8339,
    )
    event = {
        "id": 8339,
        "home_team": "South Korea",
        "away_team": "South Africa",
        "event_date": "2026-06-25T01:00:00+00:00",
        "venue_name": "BBVA Stadium, Guadalupe",
        "status": "notstarted",
    }
    assert apply_bsd_schedule_to_match(match, event) is True
    assert match.match_date == "2026年06月25日"
    assert match.match_time == "09:00"
    assert "BBVA" in (match.stadium or "")


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


def test_match_knockout_by_team_id():
    from app.ingest.bsd_link_service import list_team_pair_event_candidates

    local = Match(
        id=4,
        bracket_round="r16",
        bracket_order=3,
        round_type="knockout",
        team1_name="葡萄牙",
        team2_name="克罗地亚",
    )
    events = [
        {
            "id": 8400,
            "round_name": "Round of 16",
            "home_team_id": 491,
            "away_team_id": 494,
            "home_team": {"id": 491, "name": "Portugal"},
            "away_team": {"id": 494, "name": "Croatia"},
            "event_date": "2026-07-03T03:00:00+00:00",
            "status": "notstarted",
        },
    ]
    hits = list_team_pair_event_candidates(local, events)
    assert len(hits) == 1
    assert hits[0]["id"] == 8400


def test_match_knockout_by_team_pair():
    local = Match(
        id=3,
        bracket_round="r32",
        bracket_order=5,
        round_type="knockout",
        team1_name="哥伦比亚",
        team2_name="葡萄牙",
    )
    round_events = _group_events_by_round([
        {
            "id": 8333,
            "round_name": "Round of 32",
            "home_team": "Colombia",
            "away_team": "Portugal",
            "event_date": "2026-06-28T19:00:00+00:00",
            "status": "finished",
        },
        {
            "id": 8334,
            "round_name": "Round of 32",
            "home_team": "England",
            "away_team": "Croatia",
            "event_date": "2026-06-29T03:00:00+00:00",
            "status": "finished",
        },
        {
            "id": 8400,
            "round_name": "Round of 16",
            "home_team": "Portugal",
            "away_team": "Croatia",
            "event_date": "2026-07-03T03:00:00+00:00",
            "status": "notstarted",
        },
    ])
    hit = _match_knockout(local, round_events)
    assert hit is not None
    assert hit["id"] == 8333
