"""Shared rules for whether a match accepts predictions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.match_kickoff import parse_kickoff
from app.db.models import Match


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def match_has_live_signals(match: Match) -> bool:
    if match.minute is not None and int(match.minute) > 0:
        return True
    if match.home_score is not None or match.away_score is not None:
        return True
    return False


def is_match_predictable(
    match: Match,
    *,
    close_minutes_before: int,
    now: datetime | None = None,
) -> bool:
    now = now or _utcnow()
    if match.status not in (None, "scheduled"):
        return False
    kick = parse_kickoff(match)
    if not kick:
        return False
    if kick <= now:
        return False
    if kick - timedelta(minutes=close_minutes_before) <= now:
        return False
    if match_has_live_signals(match):
        return False
    return True
