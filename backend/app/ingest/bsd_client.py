"""BSD (Bzzoiro Sports Data) v2 HTTP client."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.ingest.quota import record_bsd_request

logger = logging.getLogger(__name__)


class BsdClient:
    def __init__(self):
        self.settings = get_settings()
        self.headers = {"Authorization": f"Token {self.settings.bsd_api_key}"}

    @property
    def configured(self) -> bool:
        return self.settings.bsd_configured()

    def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        if not self.configured:
            return {"results": [], "errors": {"config": "BSD_API_KEY not set"}}
        url = f"{self.settings.bsd_api_prefix}{path}"
        query = dict(params or {})
        query.setdefault("tz", self.settings.bsd_timezone)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=self.headers, params=query)
                resp.raise_for_status()
                record_bsd_request(1)
                return resp.json()
        except Exception as exc:
            logger.warning("BSD request failed %s: %s", path, exc)
            return {"results": [], "errors": {"request": str(exc)}}

    def _paginate(self, path: str, params: dict | None = None, *, page_size: int = 200) -> list[dict]:
        items: list[dict] = []
        offset = 0
        while True:
            query = dict(params or {})
            query.setdefault("limit", page_size)
            query.setdefault("offset", offset)
            data = self._get(path, query)
            batch = data.get("results") or []
            items.extend(batch)
            if not data.get("next") or not batch:
                break
            offset += page_size
        return items

    def list_league_events(
        self,
        *,
        league_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        status: str | None = None,
        team_id: int | None = None,
        group_name: str | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "league_id": league_id or self.settings.bsd_league_id,
        }
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if status:
            params["status"] = status
        if team_id:
            params["team_id"] = team_id
        if group_name:
            params["group_name"] = group_name
        return self._paginate("/events/", params)

    def get_all_worldcup_events(self) -> list[dict]:
        return self.list_league_events(
            date_from="2026-06-01",
            date_to="2026-07-31",
        )

    def get_live_events(self) -> list[dict]:
        data = self._get("/events/live/")
        return data.get("results") or []

    def get_event(self, event_id: int) -> dict | None:
        data = self._get(f"/events/{event_id}/")
        if data.get("errors"):
            return None
        return data if data.get("id") else None

    def get_incidents(self, event_id: int) -> list[dict]:
        data = self._get(f"/events/{event_id}/incidents/")
        return data.get("incidents") or []

    def get_standings(self, league_id: int | None = None) -> dict[str, Any]:
        lid = league_id or self.settings.bsd_league_id
        return self._get(f"/leagues/{lid}/standings/")

    def list_teams(self, league_id: int | None = None, *, limit: int = 200) -> list[dict]:
        return self._paginate(
            "/teams/",
            {"league_id": league_id or self.settings.bsd_league_id},
            page_size=limit,
        )

    def list_worldcup_squads(self, **params: Any) -> list[dict]:
        return self._paginate("/worldcup/squads/", params)


def load_team_bsd_mapping() -> dict[str, int | None]:
    settings = get_settings()
    path = settings.team_bsd_mapping_path
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_") and v is not None}
