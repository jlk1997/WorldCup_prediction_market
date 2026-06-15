"""Generate full 104-match World Cup 2026 schedule from teams_list.json.

Group-stage dates/times are **placeholders** (round-robin slot filler).
After BSD link, ingest syncs authoritative kickoff from BSD API.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from itertools import combinations
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from app.db.models import Match
from app.db.session import SessionLocal
from app.utils.team_names import canonical_team_name
from app.services.bracket_templates import build_bracket_meta_for_knockout

TEAMS_LIST = BACKEND_DIR.parent / "WorldCup2026_Teams" / "teams_list.json"
OUTPUT = BACKEND_DIR / "schedule_full.json"

STADIUMS = [
    "墨西哥城 · 阿兹特克体育场",
    "瓜达拉哈拉 · 阿克伦体育场",
    "多伦多 · BMO球场",
    "洛杉矶 · SoFi体育场",
    "亚特兰大 · 梅赛德斯奔驰球场",
    "达拉斯 · AT&T体育场",
    "迈阿密 · Hard Rock体育场",
    "休斯顿 · NRG体育场",
    "费城 · 林肯金融球场",
    "西雅图 · Lumen Field",
    "旧金山 · Levi's体育场",
    "堪萨斯城 · Arrowhead体育场",
]

KICKOFF_TIMES = ["03:00", "07:00", "10:00", "14:00", "18:00", "22:00"]

KNOCKOUT_ROUNDS: list[tuple[str, str, int]] = [
    ("r32", "三十二强", 16),
    ("r16", "十六强", 8),
    ("qf", "四分之一决赛", 4),
    ("sf", "半决赛", 2),
    ("third", "三四名决赛", 1),
    ("final", "决赛", 1),
]

ROUND_LABELS = {
    "r32": "三十二强",
    "r16": "十六强",
    "qf": "四分之一决赛",
    "sf": "半决赛",
    "third": "三四名决赛",
    "final": "决赛",
}


def _load_groups() -> dict[str, list[str]]:
    with TEAMS_LIST.open(encoding="utf-8") as f:
        teams = json.load(f)
    groups: dict[str, list[str]] = {}
    for t in teams:
        g = t.get("group", "Group_X").replace("Group_", "") + "组"
        name = canonical_team_name(t["name"])
        groups.setdefault(g, []).append(name)
    return groups


def generate_schedule() -> list[dict]:
    groups = _load_groups()
    matches: list[dict] = []
    start = datetime(2026, 6, 12)
    day_offset = 0
    stadium_idx = 0
    time_idx = 0

    def next_slot(
        group_label: str,
        team1: str,
        team2: str,
        *,
        tag: str = "",
        round_type: str = "group",
        bracket_round: str | None = None,
        bracket_order: int | None = None,
        bracket_meta: dict | None = None,
    ) -> dict:
        nonlocal day_offset, stadium_idx, time_idx
        d = start + timedelta(days=day_offset)
        item = {
            "group": f"{group_label}{(' · ' + tag) if tag else ''}",
            "date": d.strftime("%Y年%m月%d日"),
            "time": KICKOFF_TIMES[time_idx % len(KICKOFF_TIMES)],
            "team1": team1,
            "team2": team2,
            "stadium": STADIUMS[stadium_idx % len(STADIUMS)],
            "status": "scheduled",
            "round_type": round_type,
            "bracket_round": bracket_round,
            "bracket_order": bracket_order,
            "bracket_meta": bracket_meta,
        }
        time_idx += 1
        if time_idx % 3 == 0:
            day_offset += 1
        stadium_idx += 1
        return item

    for group_name, team_names in sorted(groups.items()):
        if len(team_names) < 2:
            continue
        for t1, t2 in combinations(team_names, 2):
            matches.append(next_slot(group_name, t1, t2, round_type="group"))

    day_offset = max(day_offset, 20)
    bracket_meta_map = build_bracket_meta_for_knockout()
    for round_key, round_label, count in KNOCKOUT_ROUNDS:
        for i in range(1, count + 1):
            slot_label = round_label if count == 1 else f"{round_label} 第{i}场"
            meta = bracket_meta_map.get((round_key, i))
            matches.append(
                next_slot(
                    "淘汰赛",
                    f"待定·{slot_label}A",
                    f"待定·{slot_label}B",
                    tag=round_label,
                    round_type="knockout",
                    bracket_round=round_key,
                    bracket_order=i,
                    bracket_meta=meta,
                )
            )

    return matches[:104]


def apply_to_db(matches: list[dict]) -> int:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE matches RESTART IDENTITY CASCADE"))
        for item in matches:
            db.add(
                Match(
                    group_name=item["group"],
                    match_date=item["date"],
                    match_time=item["time"],
                    team1_name=item["team1"],
                    team2_name=item["team2"],
                    stadium=item["stadium"],
                    status=item.get("status", "scheduled"),
                    round_type=item.get("round_type", "group"),
                    bracket_round=item.get("bracket_round"),
                    bracket_order=item.get("bracket_order"),
                    bracket_meta=item.get("bracket_meta"),
                )
            )
        db.commit()
        return len(matches)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Expand schedule to 104 matches")
    parser.add_argument("--apply", action="store_true", help="Write to database")
    parser.add_argument("--write-json", action="store_true", help="Write schedule_full.json")
    args = parser.parse_args()

    matches = generate_schedule()
    print(f"Generated {len(matches)} matches")

    if args.write_json or not args.apply:
        with OUTPUT.open("w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        print(f"Written {OUTPUT}")

    if args.apply:
        count = apply_to_db(matches)
        print(f"Applied {count} matches to database")


if __name__ == "__main__":
    main()
