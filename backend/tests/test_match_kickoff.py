import pytest
from datetime import datetime, timezone

from app.core.match_kickoff import parse_match_kickoff


def test_parse_chinese_date_kickoff():
    kick = parse_match_kickoff("2026年07月02日", "03:00", timezone_name="America/New_York")
    assert kick is not None
    assert kick.year == 2026
    assert kick.month == 7
    assert kick.day == 2


def test_parse_iso_date_kickoff():
    kick = parse_match_kickoff("2026-07-02", "15:30", timezone_name="UTC")
    assert kick == datetime(2026, 7, 2, 15, 30)


def test_parse_invalid_date():
    assert parse_match_kickoff("not-a-date", "12:00") is None
    assert parse_match_kickoff(None, "12:00") is None
