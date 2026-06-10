"""Parse REFERRAL_WEEKLY_RANK_REWARDS env into rank -> (points, coins)."""

from __future__ import annotations


def parse_weekly_rank_rewards(raw: str) -> dict[int, tuple[int, int]]:
    """Format: rank:points:coins or lo-hi:points:coins, comma-separated."""
    result: dict[int, tuple[int, int]] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        segments = part.split(":")
        if len(segments) != 3:
            continue
        rank_spec, pts_s, coins_s = segments[0].strip(), segments[1].strip(), segments[2].strip()
        try:
            points = int(pts_s)
            coins = int(coins_s)
        except ValueError:
            continue
        if "-" in rank_spec:
            lo_s, hi_s = rank_spec.split("-", 1)
            try:
                lo, hi = int(lo_s), int(hi_s)
            except ValueError:
                continue
            for r in range(lo, hi + 1):
                result[r] = (points, coins)
        else:
            try:
                result[int(rank_spec)] = (points, coins)
            except ValueError:
                continue
    return result


def weekly_settle_top_n(rewards_map: dict[int, tuple[int, int]]) -> int:
    return max(rewards_map.keys()) if rewards_map else 0
