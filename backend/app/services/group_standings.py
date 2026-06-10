"""Group stage standings for 48-team World Cup (12 groups × 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

GROUP_LETTERS = list("ABCDEFGHIJKL")


@dataclass
class TeamStanding:
    team: str
    group: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_diff(self) -> int:
        return self.goals_for - self.goals_against


@dataclass
class GroupTable:
    group: str
    teams: dict[str, TeamStanding] = field(default_factory=dict)

    def sorted_rows(self) -> list[TeamStanding]:
        return sorted(
            self.teams.values(),
            key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team),
        )

    @property
    def is_complete(self) -> bool:
        if len(self.teams) != 4:
            return False
        return all(r.played >= 3 for r in self.teams.values())


def parse_group_letter(group_name: str | None) -> str | None:
    if not group_name:
        return None
    name = group_name.strip()
    if name.endswith("组"):
        letter = name.replace("组", "").strip().upper()
        return letter if len(letter) == 1 and letter in GROUP_LETTERS else None
    return None


def _apply_result(row: TeamStanding, gf: int, ga: int) -> None:
    row.played += 1
    row.goals_for += gf
    row.goals_against += ga
    if gf > ga:
        row.won += 1
        row.points += 3
    elif gf < ga:
        row.lost += 1
    else:
        row.drawn += 1
        row.points += 1


def build_standings(group_matches: list) -> dict[str, GroupTable]:
    """Build tables from finished group-stage Match rows."""
    tables: dict[str, GroupTable] = {}

    for m in group_matches:
        if getattr(m, "round_type", "group") not in (None, "group"):
            continue
        if m.status != "finished":
            continue
        if m.home_score is None or m.away_score is None:
            continue
        letter = parse_group_letter(m.group_name)
        if not letter:
            continue

        table = tables.setdefault(letter, GroupTable(group=letter))
        for team in (m.team1_name, m.team2_name):
            if team and team not in table.teams and not str(team).startswith("待定"):
                table.teams[team] = TeamStanding(team=team, group=letter)

        t1, t2 = m.team1_name, m.team2_name
        if not t1 or not t2 or str(t1).startswith("待定") or str(t2).startswith("待定"):
            continue

        h, a = int(m.home_score), int(m.away_score)
        if t1 not in table.teams:
            table.teams[t1] = TeamStanding(team=t1, group=letter)
        if t2 not in table.teams:
            table.teams[t2] = TeamStanding(team=t2, group=letter)
        _apply_result(table.teams[t1], h, a)
        _apply_result(table.teams[t2], a, h)

    return tables


def rank_third_place_teams(tables: dict[str, GroupTable]) -> list[str]:
    """Return top 8 third-placed teams (2026: 12 groups → 8 best thirds)."""
    thirds: list[TeamStanding] = []
    for letter in GROUP_LETTERS:
        table = tables.get(letter)
        if not table or len(table.sorted_rows()) < 3:
            continue
        thirds.append(table.sorted_rows()[2])
    thirds.sort(key=lambda r: (-r.points, -r.goal_diff, -r.goals_for, r.team))
    return [r.team for r in thirds[:8]]


def all_group_stage_done(tables: dict[str, GroupTable]) -> bool:
    return all(tables.get(g, GroupTable(g)).is_complete for g in GROUP_LETTERS)


def tables_to_dict(tables: dict[str, GroupTable]) -> dict:
    out: dict = {"groups": {}, "third_place_qualifiers": []}
    for letter in GROUP_LETTERS:
        table = tables.get(letter)
        if not table:
            continue
        rows = table.sorted_rows()
        out["groups"][letter] = {
            "complete": table.is_complete,
            "standings": [
                {
                    "team": r.team,
                    "played": r.played,
                    "won": r.won,
                    "drawn": r.drawn,
                    "lost": r.lost,
                    "gf": r.goals_for,
                    "ga": r.goals_against,
                    "gd": r.goal_diff,
                    "points": r.points,
                }
                for r in rows
            ],
        }
    out["third_place_qualifiers"] = rank_third_place_teams(tables)
    out["all_complete"] = all_group_stage_done(tables)
    return out
