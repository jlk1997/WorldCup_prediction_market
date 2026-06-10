"""Tests for BSD team name mapping."""

import json
from pathlib import Path

from app.data.bsd_team_names import BSD_TO_LOCAL, bsd_name_to_local, normalize_group_label


def test_all_48_teams_mapped():
    teams_list = Path(__file__).resolve().parents[2] / "WorldCup2026_Teams" / "teams_list.json"
    teams = json.loads(teams_list.read_text(encoding="utf-8"))
    local_names = {t["name"] for t in teams}
    mapped_local = set(BSD_TO_LOCAL.values())
    missing = local_names - mapped_local - {"刚果民主共和国"}
    assert not missing, f"Missing BSD mapping for: {missing}"


def test_bsd_name_to_local():
    assert bsd_name_to_local("Mexico") == "墨西哥"
    assert bsd_name_to_local("DR Congo") == "刚果（金）"


def test_normalize_group_label():
    assert normalize_group_label("A组") == "Group A"
    assert normalize_group_label("Group H") == "Group H"
