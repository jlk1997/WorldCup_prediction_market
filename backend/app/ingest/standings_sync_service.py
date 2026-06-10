"""Sync BSD World Cup standings into cache."""

from __future__ import annotations

import logging

from app.core.cache import cache_get, cache_set
from app.data.bsd_team_names import bsd_name_to_local
from app.ingest.bsd_client import BsdClient

logger = logging.getLogger(__name__)

STANDINGS_CACHE_KEY = "bsd:standings:wc2026"
STANDINGS_TTL = 300


class StandingsSyncService:
    def __init__(self):
        self.client = BsdClient()

    def sync(self) -> bool:
        if not self.client.configured:
            return False
        raw = self.client.get_standings()
        if not raw or not raw.get("groups"):
            return False
        payload = self._normalize(raw)
        cache_set(STANDINGS_CACHE_KEY, payload, ttl=STANDINGS_TTL)
        return True

    def get_cached(self) -> dict | None:
        return cache_get(STANDINGS_CACHE_KEY)

    def _normalize(self, raw: dict) -> dict:
        groups_out: dict[str, list[dict]] = {}
        for group_name, rows in (raw.get("groups") or {}).items():
            normalized_group = group_name.replace("Group ", "") + "组" if group_name.startswith("Group ") else group_name
            entries = []
            for row in rows or []:
                local_name = bsd_name_to_local(row.get("team_name")) or row.get("team_name")
                entries.append({
                    "position": row.get("position"),
                    "team": local_name,
                    "played": row.get("played"),
                    "won": row.get("won"),
                    "drawn": row.get("drawn"),
                    "lost": row.get("lost"),
                    "gf": row.get("gf"),
                    "ga": row.get("ga"),
                    "gd": row.get("gd"),
                    "pts": row.get("pts"),
                    "form": row.get("form"),
                })
            groups_out[normalized_group] = entries
        return {
            "source": "bsd",
            "season": raw.get("season"),
            "groups": groups_out,
        }
