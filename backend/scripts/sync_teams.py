"""Sync team and player data from JSON sources."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.models import PlayerDetailed, Team
from app.db.session import SessionLocal
from app.services.starter_selector import update_all_starters
from app.utils.team_names import canonical_team_name, load_team_name_map, resolve_team_name


def _parse_legacy_player_entry(raw: str, position: str) -> dict | None:
    text = (raw or "").strip()
    if not text:
        return None
    name = text
    club = ""
    if "（" in text and "）" in text:
        name, rest = text.split("（", 1)
        club = rest.rsplit("）", 1)[0].replace("，队长", "").replace(",队长", "").strip()
    name = name.strip()
    if not name:
        return None
    return {"name": name, "position": position, "club": club}


def _legacy_squad_for_team(settings, team_name: str) -> list[dict]:
    path = settings.legacy_teams_json
    if not path.exists():
        return []

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    canonical = canonical_team_name(team_name)
    for team_data in data:
        db_name = team_data.get("球队名称")
        if not db_name or canonical_team_name(db_name) != canonical:
            continue
        roster = team_data.get("球员名单") or {}
        players: list[dict] = []
        for group, entries in roster.items():
            if not isinstance(entries, list):
                continue
            position = str(group)
            for entry in entries:
                parsed = _parse_legacy_player_entry(str(entry), position)
                if parsed:
                    players.append(parsed)
        return players
    return []


def _insert_player(db, team: Team, p: dict) -> bool:
    name = p.get("name", "")
    if not name:
        return False
    position = p.get("position", "")
    if "教练" in position:
        if not team.coach:
            team.coach = name
        return False

    injuries_raw = p.get("injuries")
    injury_status = None
    injury_detail = None
    if isinstance(injuries_raw, list) and injuries_raw:
        first = injuries_raw[0]
        if isinstance(first, dict):
            injury_status = first.get("status") or first.get("type") or "injured"
            injury_detail = first.get("detail") or first.get("description") or str(first)
        elif isinstance(injuries_raw, str):
            injury_detail = injuries_raw
            injury_status = "injured"
    elif isinstance(injuries_raw, str) and injuries_raw.strip():
        injury_detail = injuries_raw.strip()
        injury_status = "injured"

    db.add(
        PlayerDetailed(
            team_id=team.id,
            name=name,
            age=p.get("age"),
            position=position,
            club=p.get("club", ""),
            is_starter=False,
            height=_parse_int(p.get("height")),
            weight=_parse_int(p.get("weight")),
            preferred_foot=p.get("preferred_foot"),
            birth_date=p.get("birth_date"),
            overall_rating=p.get("overall_rating"),
            stats=p.get("stats"),
            honors=p.get("honors"),
            transfers=p.get("transfers"),
            injuries=injuries_raw if isinstance(injuries_raw, list) else None,
            injury_status=injury_status,
            injury_detail=injury_detail,
            market_value=p.get("market_value") or p.get("value"),
            form_rating=p.get("form_rating"),
        )
    )
    return True


def sync_legacy(db, settings) -> int:
    path = settings.legacy_teams_json
    if not path.exists():
        print(f"skip legacy: not found {path}")
        return 0

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for team_data in data:
        team_name = team_data.get("球队名称")
        if not team_name:
            continue

        team = db.scalar(select(Team).where(Team.name == team_name))
        if not team:
            print(f"warn: team not in db {team_name}, skip")
            continue

        avg_age_str = team_data.get("平均年龄", "").replace("岁", "")
        try:
            avg_age = float(avg_age_str)
        except ValueError:
            avg_age = None

        team.total_value = team_data.get("球队总身价", "") or team.total_value
        team.avg_age = avg_age if avg_age is not None else team.avg_age
        team.formation = team_data.get("惯用阵型", "") or team.formation
        team.coach = team_data.get("教练团队", {}).get("主教练", team.coach)
        count += 1

    print(f"legacy metadata sync: {count} teams (coach/formation only, no player overwrite)")
    return count


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int("".join(filter(str.isdigit, str(value))))
    except ValueError:
        return None


def sync_wc2026(db, settings, team_filter: str | None = None) -> int:
    base_dir = settings.teams_data_dir
    if not base_dir.exists():
        print(f"skip wc2026: not found {base_dir}")
        return 0

    name_map = load_team_name_map(base_dir)
    json_files = glob.glob(str(base_dir / "**" / "*.json"), recursive=True)
    updated = 0
    inserted = 0

    for file_path in json_files:
        if file_path.endswith("teams_list.json"):
            continue

        file_stem = Path(file_path).stem
        team_name = resolve_team_name(file_stem, name_map)
        if team_filter and team_name != team_filter:
            continue

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        team_info = data.get("team_info", {})
        squad = data.get("squad", []) or []
        if not squad:
            squad = _legacy_squad_for_team(settings, team_name)
            if squad:
                print(f"info: {team_name} squad empty in wc2026 json, filled {len(squad)} from legacy")

        team = db.scalar(select(Team).where(Team.name == team_name))
        if not team:
            print(f"warn: db team not found {team_name} (file {file_stem}.json), skip")
            continue

        team.founded = str(team_info.get("成立", team_info.get("founded_year", team_info.get("founded", ""))))
        team.city = team_info.get("城市", team_info.get("city", ""))
        team.stadium = team_info.get("主场", team_info.get("stadium", ""))
        team.capacity = str(team_info.get("容量", team_info.get("capacity", "")))
        team.total_value = team_info.get("市值", team_info.get("market_value", team.total_value))

        db.execute(delete(PlayerDetailed).where(PlayerDetailed.team_id == team.id))

        for p in squad:
            if _insert_player(db, team, p):
                inserted += 1

        updated += 1

    print(f"wc2026 sync: {updated} teams, {inserted} players inserted")
    return updated


def main():
    parser = argparse.ArgumentParser(description="Sync team data from JSON")
    parser.add_argument(
        "--source",
        choices=["legacy", "wc2026", "all"],
        default="wc2026",
        help="legacy=metadata only; wc2026=full players; all=both",
    )
    parser.add_argument("--team", default=None, help="Sync single team by DB name")
    args = parser.parse_args()

    settings = get_settings()
    db = SessionLocal()
    try:
        if args.source in ("legacy", "all"):
            sync_legacy(db, settings)
        if args.source in ("wc2026", "all"):
            sync_wc2026(db, settings, team_filter=args.team)
        update_all_starters(db)
        db.commit()
        print("[OK] sync complete")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] sync failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
