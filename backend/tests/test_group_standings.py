from types import SimpleNamespace

from app.services.group_standings import build_standings, rank_third_place_teams, tables_to_dict


def _match(team1, team2, hg, ag, group="A组", status="finished"):
    return SimpleNamespace(
        round_type="group",
        group_name=group,
        team1_name=team1,
        team2_name=team2,
        home_score=hg,
        away_score=ag,
        status=status,
    )


def test_group_standings_points_and_ranking():
    matches = [
        _match("阿根廷", "巴西", 2, 1, "A组"),
        _match("阿根廷", "智利", 1, 1, "A组"),
        _match("阿根廷", "秘鲁", 3, 0, "A组"),
        _match("巴西", "智利", 2, 0, "A组"),
        _match("巴西", "秘鲁", 1, 0, "A组"),
        _match("智利", "秘鲁", 2, 1, "A组"),
    ]
    tables = build_standings(matches)
    rows = tables["A"].sorted_rows()
    assert rows[0].team == "阿根廷"
    assert rows[0].points == 7
    assert rows[1].team == "巴西"


def test_third_place_ranking():
    matches = []
    for group, teams in [("A", ("t1", "t2", "t3", "t4")), ("B", ("u1", "u2", "u3", "u4"))]:
        g = f"{group}组"
        pairs = [(teams[0], teams[1], 1, 0), (teams[0], teams[2], 1, 0), (teams[0], teams[3], 1, 0),
                 (teams[1], teams[2], 1, 0), (teams[1], teams[3], 1, 0), (teams[2], teams[3], 2, 1)]
        for a, b, h, aw in pairs:
            matches.append(_match(a, b, h, aw, g))
    tables = build_standings(matches)
    thirds = rank_third_place_teams(tables)
    assert len(thirds) == 2
    payload = tables_to_dict(tables)
    assert "A" in payload["groups"]
