"""Build BSD team ID mapping for local Chinese team names."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.data.bsd_team_names import BSD_TO_LOCAL, bsd_name_to_local
from app.ingest.bsd_client import BsdClient
from app.utils.team_names import canonical_team_name, load_team_name_map


def main():
    parser = argparse.ArgumentParser(description="Build BSD team ID mapping")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    settings = get_settings()
    output = args.output or settings.team_bsd_mapping_path
    client = BsdClient()
    if not client.configured:
        print("BSD_API_KEY not configured")
        sys.exit(1)

    teams = client.list_teams()
    eng_to_id: dict[str, int] = {}
    for team in teams:
        name = team.get("name")
        tid = team.get("id")
        if name and tid:
            eng_to_id[name] = int(tid)

    local_names = set(load_team_name_map(settings.teams_data_dir).values())
    mapping: dict[str, int | None] = {"_comment": "Local team name -> BSD team ID"}
    missing: list[str] = []

    for local in sorted(local_names):
        canonical = canonical_team_name(local)
        eng = None
        for e, zh in BSD_TO_LOCAL.items():
            if zh == canonical:
                eng = e
                break
        tid = eng_to_id.get(eng) if eng else None
        if tid is None and eng:
            for api_name, api_id in eng_to_id.items():
                if bsd_name_to_local(api_name) == canonical:
                    tid = api_id
                    break
        mapping[canonical] = tid
        if tid is None:
            missing.append(canonical)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"Wrote {output} ({len(mapping)-1} teams, {len(missing)} missing)")
    if missing:
        print("Missing:", ", ".join(missing))


if __name__ == "__main__":
    main()
