"""Tests for BSD live sync apply logic."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.db.models import Match
from app.ingest.bsd_adapter import InternalFixture
from app.ingest.live_sync_service import _apply_internal_fixture


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
