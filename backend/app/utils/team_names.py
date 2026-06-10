"""Team name mapping between JSON files, schedule, and database records."""

from __future__ import annotations

import json
from pathlib import Path

# Alternate names -> canonical DB team name (teams.name)
ALIASES_TO_DB: dict[str, str] = {
    "刚果民主共和国": "刚果（金）",
}

# DB name -> schedule/JSON display name (optional reverse for UI)
DB_TO_DISPLAY: dict[str, str] = {
    "刚果（金）": "刚果民主共和国",
}


def canonical_team_name(name: str) -> str:
    """Return the name stored in PostgreSQL teams table."""
    return ALIASES_TO_DB.get(name, name)


def display_team_name(db_name: str) -> str:
    """Return user-facing name for UI when DB uses shortened form."""
    return DB_TO_DISPLAY.get(db_name, db_name)


def load_team_name_map(teams_data_dir: Path) -> dict[str, str]:
    """Build mapping from JSON filename stem to canonical DB team name."""
    mapping = dict(ALIASES_TO_DB)
    list_path = teams_data_dir / "teams_list.json"
    if not list_path.exists():
        return mapping

    with list_path.open(encoding="utf-8") as f:
        teams = json.load(f)

    for item in teams:
        raw = item.get("name")
        if not raw:
            continue
        mapping[raw] = canonical_team_name(raw)

    for json_path in teams_data_dir.rglob("*.json"):
        if json_path.name == "teams_list.json":
            continue
        stem = json_path.stem
        mapping[stem] = canonical_team_name(stem)

    return mapping


def resolve_team_name(file_stem: str, name_map: dict[str, str] | None = None) -> str:
    if name_map is None:
        return canonical_team_name(file_stem)
    return name_map.get(file_stem, canonical_team_name(file_stem))
