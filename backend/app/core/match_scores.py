"""Normalize match scores so home_score = team1, away_score = team2 for settlement."""

from __future__ import annotations


def scores_for_team1_team2(
    team1_name: str | None,
    team2_name: str | None,
    bsd_home_name: str | None,
    bsd_away_name: str | None,
    bsd_home_score: int | None,
    bsd_away_score: int | None,
) -> tuple[int | None, int | None]:
    """Map provider home/away scores onto team1/team2 columns."""
    if bsd_home_score is None and bsd_away_score is None:
        return None, None

    if not team1_name or not team2_name or not bsd_home_name or not bsd_away_name:
        return bsd_home_score, bsd_away_score

    if bsd_home_name == team1_name and bsd_away_name == team2_name:
        return bsd_home_score, bsd_away_score
    if bsd_home_name == team2_name and bsd_away_name == team1_name:
        return bsd_away_score, bsd_home_score

    return bsd_home_score, bsd_away_score


def result_pick_from_team_scores(
    team1_score: int | None,
    team2_score: int | None,
) -> str | None:
    """Return home/draw/away where home=team1 win, away=team2 win."""
    if team1_score is None and team2_score is None:
        return None
    t1 = team1_score if team1_score is not None else 0
    t2 = team2_score if team2_score is not None else 0
    if t1 > t2:
        return "home"
    if t1 < t2:
        return "away"
    return "draw"
