"""Convert BSD event payloads to internal fixture representation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings
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
    local_date: str | None = None
    local_time: str | None = None
    venue: str | None = None


def _event_venue(event: dict) -> str | None:
    for key in ("venue_name", "venue", "stadium", "stadium_name"):
        val = event.get(key)
        if val:
            return str(val)
    return None


def bsd_event_to_local_schedule(event: dict) -> tuple[str | None, str | None, str | None]:
    """Map BSD event_date (ISO, tz-aware) to Chinese date + HH:MM in bsd_timezone."""
    raw = event.get("event_date")
    venue = _event_venue(event)
    if not raw:
        return None, None, venue
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None, None, venue
    tz = ZoneInfo(get_settings().bsd_timezone)
    local = dt.astimezone(tz)
    date_cn = f"{local.year}年{local.month:02d}月{local.day:02d}日"
    return date_cn, local.strftime("%H:%M"), venue


def map_bsd_status(raw: str | None) -> str:
    return BSD_STATUS_MAP.get((raw or "notstarted").lower(), "scheduled")


def resolve_event_status(event: dict) -> str:
    """Map BSD status, inferring finished/live when provider lags on status field."""
    mapped = map_bsd_status(event.get("status"))
    if mapped in ("live", "finished", "postponed"):
        return mapped
    minute = event.get("current_minute")
    period = (event.get("period") or "").lower()
    if minute is not None and int(minute) >= 90:
        return "finished"
    if any(token in period for token in ("finished", "fulltime", "full time", "ft", "ended")):
        return "finished"
    home = event.get("home_score")
    away = event.get("away_score")
    if home is not None and away is not None and minute is not None and int(minute) > 0:
        return "live"
    return mapped


def _bsd_team_raw_name(raw: str | dict | None) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        for key in ("name", "short_name", "full_name", "display_name"):
            val = raw.get(key)
            if val:
                return str(val).strip()
        return None
    text = str(raw).strip()
    return text or None


def _bsd_team_id(raw: str | dict | None, event: dict, side: str) -> int | None:
    id_key = f"{side}_team_id"
    if event.get(id_key) is not None:
        return int(event[id_key])
    if isinstance(raw, dict) and raw.get("id") is not None:
        return int(raw["id"])
    return None


def event_bsd_team_ids(event: dict) -> frozenset[int] | None:
    home_raw = event.get("home_team")
    away_raw = event.get("away_team")
    home_id = _bsd_team_id(home_raw, event, "home")
    away_id = _bsd_team_id(away_raw, event, "away")
    if home_id is not None and away_id is not None:
        return frozenset({home_id, away_id})
    return None


def event_to_internal(event: dict, *, venue_name: str | None = None) -> InternalFixture:
    home_raw = event.get("home_team")
    away_raw = event.get("away_team")
    home_name_raw = _bsd_team_raw_name(home_raw)
    away_name_raw = _bsd_team_raw_name(away_raw)
    home = (
        bsd_name_to_local(home_name_raw)
        if home_name_raw and not is_knockout_placeholder(home_name_raw)
        else None
    )
    away = (
        bsd_name_to_local(away_name_raw)
        if away_name_raw and not is_knockout_placeholder(away_name_raw)
        else None
    )
    event_date = event.get("event_date")
    local_date, local_time, venue = bsd_event_to_local_schedule(event)
    return InternalFixture(
        external_id=int(event["id"]),
        provider="bsd",
        home_name=home,
        away_name=away,
        status=resolve_event_status(event),
        home_score=event.get("home_score"),
        away_score=event.get("away_score"),
        minute=event.get("current_minute"),
        period=event.get("period") or None,
        group_name=event.get("group_name"),
        round_name=event.get("round_name"),
        round_number=event.get("round_number"),
        event_date=(event_date[:10] if event_date else None),
        local_date=local_date,
        local_time=local_time,
        venue=venue or venue_name,
    )


def team_pair_key(name_a: str | None, name_b: str | None) -> frozenset[str] | None:
    if not name_a or not name_b:
        return None
    return frozenset({name_a, name_b})
