"""Parse match kickoff from DB date/time fields (中文日期 or ISO)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.db.models import Match

_CN_DATE = re.compile(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$")


def parse_match_kickoff(
    match_date: str | None,
    match_time: str | None = None,
    *,
    timezone_name: str | None = None,
) -> datetime | None:
    if not match_date:
        return None
    raw_date = match_date.strip()
    t = (match_time or "00:00").strip()
    naive: datetime | None = None

    cn = _CN_DATE.match(raw_date)
    if cn:
        try:
            parts = t.split(":")
            hh = int(parts[0])
            mm = int(parts[1]) if len(parts) > 1 else 0
            naive = datetime(int(cn.group(1)), int(cn.group(2)), int(cn.group(3)), hh, mm)
        except (ValueError, IndexError):
            return None
    else:
        try:
            naive = datetime.fromisoformat(f"{raw_date}T{t}")
        except ValueError:
            return None

    tz = ZoneInfo(timezone_name or get_settings().bsd_timezone)
    local = naive.replace(tzinfo=tz)
    return local.astimezone(timezone.utc).replace(tzinfo=None)


def parse_kickoff(m: Match) -> datetime | None:
    return parse_match_kickoff(m.match_date, m.match_time)
