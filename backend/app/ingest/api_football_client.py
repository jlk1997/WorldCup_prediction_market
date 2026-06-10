# DEPRECATED: replaced by BSD (app.ingest.bsd_client). Kept for reference only.
"""API-Football HTTP client."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

from app.ingest.quota import can_request, record_request

logger = logging.getLogger(__name__)

LIVE_STATUSES = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT"}


class ApiFootballClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.api_football_base_url.rstrip("/")
        self.headers = {
            "x-apisports-key": self.settings.api_football_key,
        }

    @property
    def configured(self) -> bool:
        return self.settings.api_football_configured()

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"response": [], "errors": {"config": "API_FOOTBALL_KEY not set"}}
        if not can_request():
            logger.warning("API-Football daily quota exceeded")
            return {"response": [], "errors": {"quota": "daily limit reached"}}
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=self.headers, params=params or {})
                resp.raise_for_status()
                record_request(1)
                return resp.json()
        except Exception as exc:
            logger.warning("API-Football request failed: %s", exc)
            return {"response": [], "errors": {"request": str(exc)}}

    def get_fixtures_by_team(self, team_id: int, season: int | None = None) -> list[dict]:
        season = season or self.settings.api_football_season
        data = self._get("/fixtures", {"team": team_id, "season": season})
        return data.get("response") or []

    def get_live_fixtures(self) -> list[dict]:
        data = self._get("/fixtures", {"live": "all"})
        return data.get("response") or []

    def get_fixture_by_id(self, fixture_id: int) -> dict | None:
        data = self._get("/fixtures", {"id": fixture_id})
        items = data.get("response") or []
        return items[0] if items else None

    def get_league_fixtures(self, league_id: int | None = None, season: int | None = None) -> list[dict]:
        league_id = league_id or self.settings.api_football_league_id
        season = season or self.settings.api_football_season
        data = self._get("/fixtures", {"league": league_id, "season": season})
        return data.get("response") or []

    def search_team(self, query: str) -> list[dict]:
        data = self._get("/teams", {"search": query})
        return data.get("response") or []

    def get_head_to_head(self, team1_id: int, team2_id: int, last: int = 5) -> list[dict]:
        data = self._get("/fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": last})
        return data.get("response") or []

    def get_fixture_events(self, fixture_id: int) -> list[dict]:
        data = self._get("/fixtures/events", {"fixture": fixture_id})
        return data.get("response") or []


def load_team_api_mapping() -> dict[str, int | None]:
    settings = get_settings()
    path = settings.team_api_mapping_path
    if not path.exists():
        from app.data.national_team_ids import NATIONAL_TEAM_IDS

        return dict(NATIONAL_TEAM_IDS)
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    mapping = {k: v for k, v in raw.items() if not k.startswith("_")}

    from app.utils.team_names import ALIASES_TO_DB

    for alias, canonical in ALIASES_TO_DB.items():
        if alias in mapping and canonical not in mapping:
            mapping[canonical] = mapping[alias]
        if canonical in mapping and alias not in mapping:
            mapping[alias] = mapping[canonical]

    id_to_names: dict[int, list[str]] = {}
    for name, tid in mapping.items():
        if tid is None:
            continue
        id_to_names.setdefault(tid, []).append(name)
    for tid, names in id_to_names.items():
        if len(names) > 1:
            logger.warning("team_api_mapping 重复 ID %s: %s", tid, ", ".join(names))

    return mapping
