"""Parse season leaderboard rank reward config."""

from __future__ import annotations


def parse_season_rank_rewards(raw: str) -> dict[int, tuple[int, int, int]]:
    """Format: rank:season_points:coins:redeem_points or lo-hi:pts:coins:redeem, comma-separated."""
    result: dict[int, tuple[int, int, int]] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        segments = part.split(":")
        if len(segments) not in (3, 4):
            continue
        rank_spec = segments[0].strip()
        try:
            season_pts = int(segments[1].strip())
            coins = int(segments[2].strip())
            redeem = int(segments[3].strip()) if len(segments) == 4 else 0
        except ValueError:
            continue
        reward = (season_pts, coins, redeem)
        if "-" in rank_spec:
            lo_s, hi_s = rank_spec.split("-", 1)
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                continue
            for r in range(lo, hi + 1):
                result[r] = reward
        else:
            try:
                result[int(rank_spec)] = reward
            except ValueError:
                continue
    return result


def season_settle_top_n(rewards_map: dict[int, tuple[int, int, int]]) -> int:
    return max(rewards_map.keys()) if rewards_map else 0
