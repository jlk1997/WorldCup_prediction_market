"""Normalize BSD incident payloads for storage."""

from __future__ import annotations

INCIDENT_TYPE_MAP = {
    "goal": "Goal",
    "card": "Card",
    "substitution": "subst",
    "var": "Var",
}


def normalize_bsd_incidents(raw_incidents: list[dict]) -> list[dict]:
    items = []
    for ev in raw_incidents:
        raw_type = (ev.get("incident_type") or ev.get("type") or "").lower()
        detail = ev.get("incident_class") or ev.get("detail") or ev.get("reason")
        items.append({
            "minute": ev.get("minute") or ev.get("time"),
            "extra": ev.get("added_time") or ev.get("extra"),
            "type": INCIDENT_TYPE_MAP.get(raw_type, ev.get("incident_type") or ev.get("type")),
            "detail": detail,
            "team": ev.get("team_name") or ev.get("team"),
            "player": ev.get("player_name") or ev.get("player"),
            "assist": ev.get("assist_name") or ev.get("assist"),
        })
    return items
