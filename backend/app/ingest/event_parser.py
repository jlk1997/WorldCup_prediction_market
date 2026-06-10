"""Normalize API-Football fixture events for storage."""

from __future__ import annotations


def normalize_events(raw_events: list[dict]) -> list[dict]:
    items = []
    for ev in raw_events:
        time_info = ev.get("time") or {}
        team = ev.get("team") or {}
        player = ev.get("player") or {}
        assist = ev.get("assist") or {}
        items.append({
            "minute": time_info.get("elapsed"),
            "extra": time_info.get("extra"),
            "type": ev.get("type") or ev.get("detail"),
            "detail": ev.get("detail"),
            "team": team.get("name"),
            "player": player.get("name"),
            "assist": assist.get("name") if assist else None,
        })
    return items
