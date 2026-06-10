"""Normalize team pair for symmetric cache keys."""


def normalize_match_pair(team1: str, team2: str) -> tuple[str, str]:
    """Return lexicographically ordered pair for deduplicated cache lookup."""
    if team1 <= team2:
        return team1, team2
    return team2, team1
