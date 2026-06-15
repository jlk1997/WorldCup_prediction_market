"""Tests for BSD live sync apply logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.db.models import Match
from app.ingest.bsd_adapter import InternalFixture
from app.ingest.live_sync_service import _apply_internal_fixture, _should_poll_match


def test_apply_internal_fixture_swaps_scores_when_bsd_home_is_team2():
    match = Match(
        id=2,
        team1_name="墨西哥",
        team2_name="南非",
        status="scheduled",
        external_fixture_id=8288,
    )
    fixture = InternalFixture(
        external_id=8288,
        provider="bsd",
        home_name="南非",
        away_name="墨西哥",
        status="finished",
        home_score=1,
        away_score=2,
        minute=90,
        period="2nd_half",
        group_name="Group A",
        round_name=None,
        round_number=None,
        event_date="2026-06-11",
        venue=None,
    )
    client = MagicMock()
    client.get_incidents.return_value = []
    assert _apply_internal_fixture(match, fixture, client) is True
    assert match.home_score == 2
    assert match.away_score == 1


def test_apply_internal_fixture_updates_scores():
    match = Match(
        id=1,
        team1_name="墨西哥",
        team2_name="南非",
        status="scheduled",
        external_fixture_id=8287,
    )
    fixture = InternalFixture(
        external_id=8287,
        provider="bsd",
        home_name="墨西哥",
        away_name="南非",
        status="live",
        home_score=1,
        away_score=0,
        minute=34,
        period="1st_half",
        group_name="Group A",
        round_name=None,
        round_number=None,
        event_date="2026-06-11",
        venue=None,
    )
    client = MagicMock()
    client.get_incidents.return_value = [
        {"minute": 12, "incident_type": "goal", "player_name": "Test", "team_name": "Mexico"},
    ]
    assert _apply_internal_fixture(match, fixture, client) is True
    assert match.status == "live"
    assert match.home_score == 1
    assert match.external_fixture_id == 8287
    assert match.external_provider == "bsd"
    assert match.events_json
    assert match.live_updated_at is not None


def test_should_poll_match_uses_parsed_kickoff(monkeypatch):
    now = datetime(2026, 6, 15, 12, 0, 0)
    near_end = now + timedelta(hours=48)
    match = Match(
        id=3,
        team1_name="墨西哥",
        team2_name="南非",
        status="scheduled",
        match_date="2026-06-12",
        match_time="07:00",
        external_fixture_id=999,
    )
    far = Match(
        id=4,
        team1_name="A",
        team2_name="B",
        status="scheduled",
        match_date="2026-07-15",
        match_time="12:00",
        external_fixture_id=1000,
    )
    old_finished = Match(
        id=5,
        team1_name="C",
        team2_name="D",
        status="finished",
        match_date="2026-06-01",
        match_time="12:00",
        external_fixture_id=1001,
    )

    def fake_kickoff(m: Match):
        if m.id == 3:
            return datetime(2026, 6, 12, 7, 0)
        if m.id == 4:
            return datetime(2026, 7, 15, 12, 0)
        if m.id == 5:
            return datetime(2026, 6, 1, 12, 0)
        return None

    monkeypatch.setattr("app.ingest.live_sync_service.parse_kickoff", fake_kickoff)
    assert _should_poll_match(match, now, near_end) is True
    assert _should_poll_match(far, now, near_end) is False
    assert _should_poll_match(old_finished, now, near_end) is False
