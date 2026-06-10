"""Convert BSD event payloads to internal fixture representation."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.bsd_team_names import bsd_name_to_local, is_knockout_placeholder

BSD_STATUS_MAP = {
    "notstarted": "scheduled",
    "inprogress": "live",
    "penalties": "live",
    "finished": "finished",
    "postponed": "postponed",
    "cancelled": "postponed",
}

LOCAL_BRACKET_TO_BSD_ROUND = {
    "r32": "Round of 32",
    "r16": "Round of 16",
    "qf": "Quarterfinals",
    "sf": "Semifinals",
    "third": "Match for 3rd place",
    "final": "Final",
}


@dataclass
class InternalFixture:
    external_id: int
    provider: str
    home_name: str | None
    away_name: str | None
    status: str
    home_score: int | None
    away_score: int | None
    minute: int | None
    period: str | None
    group_name: str | None
    round_name: str | None
    round_number: int | None
    event_date: str | None
    venue: str | None


def map_bsd_status(raw: str | None) -> str:
    return BSD_STATUS_MAP.get((raw or "notstarted").lower(), "scheduled")


def event_to_internal(event: dict, *, venue_name: str | None = None) -> InternalFixture:
    home_raw = event.get("home_team")
    away_raw = event.get("away_team")
    home = bsd_name_to_local(home_raw) if home_raw and not is_knockout_placeholder(home_raw) else None
    away = bsd_name_to_local(away_raw) if away_raw and not is_knockout_placeholder(away_raw) else None
    event_date = event.get("event_date")
    return InternalFixture(
        external_id=int(event["id"]),
        provider="bsd",
        home_name=home,
        away_name=away,
        status=map_bsd_status(event.get("status")),
        home_score=event.get("home_score"),
        away_score=event.get("away_score"),
        minute=event.get("current_minute"),
        period=event.get("period") or None,
        group_name=event.get("group_name"),
        round_name=event.get("round_name"),
        round_number=event.get("round_number"),
        event_date=(event_date[:10] if event_date else None),
        venue=venue_name,
    )


def team_pair_key(name_a: str | None, name_b: str | None) -> frozenset[str] | None:
    if not name_a or not name_b:
        return None
    return frozenset({name_a, name_b})
