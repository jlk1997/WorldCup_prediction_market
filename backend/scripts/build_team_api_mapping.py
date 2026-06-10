"""Build or refresh team_api_mapping.json using verified IDs + optional API search."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.national_team_ids import NATIONAL_TEAM_IDS
from app.ingest.api_football_client import ApiFootballClient
from app.utils.team_names import canonical_team_name

MAPPING_PATH = BACKEND_DIR / "data" / "team_api_mapping.json"
TEAMS_LIST = BACKEND_DIR.parent / "WorldCup2026_Teams" / "teams_list.json"

SEARCH_EN = {
    "墨西哥": "Mexico",
    "韩国": "South Korea",
    "南非": "South Africa",
    "捷克": "Czech Republic",
    "加拿大": "Canada",
    "瑞士": "Switzerland",
    "卡塔尔": "Qatar",
    "波黑": "Bosnia",
    "巴西": "Brazil",
    "摩洛哥": "Morocco",
    "苏格兰": "Scotland",
    "海地": "Haiti",
    "美国": "USA",
    "澳大利亚": "Australia",
    "巴拉圭": "Paraguay",
    "土耳其": "Turkey",
    "德国": "Germany",
    "厄瓜多尔": "Ecuador",
    "科特迪瓦": "Ivory Coast",
    "库拉索": "Curacao",
    "荷兰": "Netherlands",
    "日本": "Japan",
    "突尼斯": "Tunisia",
    "瑞典": "Sweden",
    "比利时": "Belgium",
    "伊朗": "Iran",
    "埃及": "Egypt",
    "新西兰": "New Zealand",
    "西班牙": "Spain",
    "乌拉圭": "Uruguay",
    "沙特阿拉伯": "Saudi Arabia",
    "佛得角": "Cape Verde",
    "法国": "France",
    "塞内加尔": "Senegal",
    "挪威": "Norway",
    "伊拉克": "Iraq",
    "阿根廷": "Argentina",
    "奥地利": "Austria",
    "阿尔及利亚": "Algeria",
    "约旦": "Jordan",
    "葡萄牙": "Portugal",
    "哥伦比亚": "Colombia",
    "乌兹别克斯坦": "Uzbekistan",
    "刚果民主共和国": "Congo DR",
    "刚果（金）": "Congo DR",
    "英格兰": "England",
    "克罗地亚": "Croatia",
    "巴拿马": "Panama",
    "加纳": "Ghana",
}


def load_local_teams() -> list[str]:
    if TEAMS_LIST.exists():
        with TEAMS_LIST.open(encoding="utf-8") as f:
            return [t["name"] for t in json.load(f)]
    return [k for k in NATIONAL_TEAM_IDS if not k.startswith("_")]


def validate_unique(mapping: dict[str, int | None]) -> list[str]:
    seen: dict[int, str] = {}
    errors: list[str] = []
    for name, tid in mapping.items():
        if name.startswith("_") or tid is None:
            continue
        if tid in seen:
            errors.append(f"重复 ID {tid}: {seen[tid]} 与 {name}")
        else:
            seen[tid] = name
    return errors


def main():
    parser = argparse.ArgumentParser(description="Build API-Football team ID mapping")
    parser.add_argument("--dry-run", action="store_true", help="Print only, do not write file")
    parser.add_argument("--api-override", action="store_true", help="Try API search when key is set")
    args = parser.parse_args()

    client = ApiFootballClient()
    mapping: dict = {
        "_comment": "Local team name -> API-Football team ID. Prefer scripts.build_team_api_mapping.",
        "_search_en": SEARCH_EN,
    }

    primary_ids: dict[str, int | None] = {}
    for raw_name in load_local_teams():
        db_name = canonical_team_name(raw_name)
        team_id = NATIONAL_TEAM_IDS.get(raw_name) or NATIONAL_TEAM_IDS.get(db_name)

        if args.api_override and client.configured and team_id is None:
            query = SEARCH_EN.get(raw_name, SEARCH_EN.get(db_name, raw_name))
            results = client.search_team(query)
            for item in results:
                team = item.get("team") or {}
                if team.get("national"):
                    team_id = team.get("id")
                    break

        mapping[raw_name] = team_id
        primary_ids[db_name] = team_id
        if db_name != raw_name:
            mapping[db_name] = team_id
        print(f"{raw_name} -> {team_id}")

    errors = validate_unique(primary_ids)
    if errors:
        print("\n[WARN] 映射校验问题:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    if not args.dry_run:
        MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MAPPING_PATH.open("w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"\nWritten {MAPPING_PATH} ({len([k for k in mapping if not k.startswith('_')])} entries)")
    else:
        print(json.dumps(mapping, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
