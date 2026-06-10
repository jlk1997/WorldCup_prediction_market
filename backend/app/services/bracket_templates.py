"""Knockout bracket templates and team resolution."""

from __future__ import annotations

from app.services.group_standings import GROUP_LETTERS, GroupTable, all_group_stage_done, rank_third_place_teams

# R16/QF/SF feed from prior round winners (bracket_order)
R16_FEEDS: list[tuple[int, int]] = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
QF_FEEDS: list[tuple[int, int]] = [(1, 2), (3, 4), (5, 6), (7, 8)]
SF_FEEDS: list[tuple[int, int]] = [(1, 2), (3, 4)]
FINAL_FEEDS: tuple[int, int] = (1, 2)
THIRD_FEEDS: tuple[int, int] = (1, 2)  # losers of SF


def build_r32_pairings(tables: dict[str, GroupTable], third_teams: list[str], *, require_full: bool = False) -> list[tuple[str, str]]:
    """Build R32 pairings from completed groups + up to 8 third-place qualifiers."""
    pool: list[str] = []
    for letter in GROUP_LETTERS:
        table = tables.get(letter)
        if not table or not table.is_complete:
            continue
        rows = table.sorted_rows()
        if len(rows) >= 1:
            pool.append(rows[0].team)
        if len(rows) >= 2:
            pool.append(rows[1].team)

    if len(third_teams) >= 8:
        pool.extend(third_teams[:8])
    elif require_full and all_group_stage_done(tables):
        pool.extend(third_teams)

    if require_full and len(pool) < 32:
        return []

    pairs: list[tuple[str, str]] = []
    for i in range(0, len(pool) - (len(pool) % 2), 2):
        pairs.append((pool[i], pool[i + 1]))
    return pairs


def build_bracket_meta_for_knockout() -> dict[tuple[str, int], dict]:
    """Default bracket_meta for seeded knockout matches."""
    meta: dict[tuple[str, int], dict] = {}

    for i in range(1, 17):
        meta[("r32", i)] = {"pair_index": i - 1, "source": "group_standings"}

    for i, (a, b) in enumerate(R16_FEEDS, 1):
        meta[("r16", i)] = {
            "home_feed": {"round": "r32", "order": a},
            "away_feed": {"round": "r32", "order": b},
        }

    for i, (a, b) in enumerate(QF_FEEDS, 1):
        meta[("qf", i)] = {
            "home_feed": {"round": "r16", "order": a},
            "away_feed": {"round": "r16", "order": b},
        }

    for i, (a, b) in enumerate(SF_FEEDS, 1):
        meta[("sf", i)] = {
            "home_feed": {"round": "qf", "order": a},
            "away_feed": {"round": "qf", "order": b},
        }

    a, b = FINAL_FEEDS
    meta[("final", 1)] = {
        "home_feed": {"round": "sf", "order": a},
        "away_feed": {"round": "sf", "order": b},
    }

    a, b = THIRD_FEEDS
    meta[("third", 1)] = {
        "home_feed": {"round": "sf", "order": a, "loser": True},
        "away_feed": {"round": "sf", "order": b, "loser": True},
    }

    return meta


def is_placeholder_name(name: str | None) -> bool:
    if not name:
        return True
    return name.startswith("待定")


def match_winner_name(match) -> str | None:
    if match.status != "finished" or match.home_score is None or match.away_score is None:
        return None
    if match.home_score > match.away_score:
        return match.team1_name
    if match.home_score < match.away_score:
        return match.team2_name
    return None


def match_loser_name(match) -> str | None:
    if match.status != "finished" or match.home_score is None or match.away_score is None:
        return None
    if match.home_score > match.away_score:
        return match.team2_name
    if match.home_score < match.away_score:
        return match.team1_name
    return None
