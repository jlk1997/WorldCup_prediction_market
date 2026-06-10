"""Enrich team records from local WorldCup2026 JSON when DB fields are empty."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DataSyncLog, Team
from app.utils.team_names import load_team_name_map

logger = logging.getLogger(__name__)


class TeamEnrichService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _find_team_json(self, teams_dir: Path, name_map: dict[str, str], canonical: str) -> Path | None:
        for stem, db_name in name_map.items():
            if db_name != canonical:
                continue
            for candidate in teams_dir.rglob(f"{stem}.json"):
                if candidate.name != "teams_list.json":
                    return candidate
        return None

    def sync(self) -> dict:
        teams_dir = self.settings.teams_data_dir
        name_map = load_team_name_map(teams_dir)
        updated = 0

        for team in self.db.scalars(select(Team)).all():
            json_path = self._find_team_json(teams_dir, name_map, team.name)
            if not json_path:
                continue

            try:
                with json_path.open(encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            info = data.get("team_info") or data
            changed = False
            if not team.stadium and info.get("stadium"):
                team.stadium = str(info["stadium"])[:200]
                changed = True
            if not team.city and info.get("city"):
                team.city = str(info["city"])[:100]
                changed = True
            if not team.founded and info.get("founded"):
                team.founded = str(info["founded"])[:50]
                changed = True
            if not team.formation and info.get("formation"):
                team.formation = str(info["formation"])[:50]
                changed = True
            if changed:
                updated += 1

        self.db.add(DataSyncLog(source="team_enrich", status="ok", records=updated))
        self.db.commit()
        logger.info("Team enrich updated %s teams", updated)
        return {"updated": updated, "status": "ok"}
