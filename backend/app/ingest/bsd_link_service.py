"""Link local Match rows to BSD event IDs."""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.bsd_team_names import normalize_group_label
from app.db.models import Match
from app.core.match_kickoff import parse_kickoff, parse_match_kickoff
from app.ingest.bsd_adapter import LOCAL_BRACKET_TO_BSD_ROUND, event_to_internal, team_pair_key
from app.ingest.bsd_client import BsdClient

logger = logging.getLogger(__name__)


def _group_events_by_round(events: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("group_name"):
            continue
        round_name = event.get("round_name")
        if round_name:
            grouped[round_name].append(event)
    for items in grouped.values():
        items.sort(key=lambda e: (e.get("event_date") or "", e.get("id") or 0))
    return grouped


def _bsd_event_kickoff(event: dict):
    raw = event.get("event_date") or ""
    if not raw:
        return None
    date_part = raw[:10]
    time_part = "00:00"
    if "T" in raw and len(raw) >= 16:
        time_part = raw[11:16]
    return parse_match_kickoff(date_part, time_part)


def list_group_event_candidates(local: Match, bsd_events: list[dict]) -> list[dict]:
    local_group = normalize_group_label(local.group_name)
    pair = team_pair_key(local.team1_name, local.team2_name)
    if not local_group or not pair:
        return []
    out: list[dict] = []
    for event in bsd_events:
        if normalize_group_label(event.get("group_name")) != local_group:
            continue
        internal = event_to_internal(event)
        event_pair = team_pair_key(internal.home_name, internal.away_name)
        if event_pair and event_pair == pair:
            out.append(event)
    return out


def pick_best_bsd_event(local: Match, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    local_kick = parse_kickoff(local)

    def rank(event: dict) -> tuple:
        internal = event_to_internal(event)
        status_rank = {"finished": 0, "live": 1, "scheduled": 2}.get(internal.status, 3)
        kick = _bsd_event_kickoff(event)
        if local_kick and kick:
            delta = abs((kick - local_kick).total_seconds())
        else:
            delta = 999999.0
        return (status_rank, delta, int(event.get("id") or 0))

    return min(candidates, key=rank)


def _match_group_stage(local: Match, bsd_events: list[dict]) -> dict | None:
    candidates = list_group_event_candidates(local, bsd_events)
    return pick_best_bsd_event(local, candidates)


def _match_knockout(local: Match, round_events: dict[str, list[dict]]) -> dict | None:
    bracket_round = local.bracket_round
    bracket_order = local.bracket_order
    if not bracket_round or not bracket_order:
        return None
    bsd_round = LOCAL_BRACKET_TO_BSD_ROUND.get(bracket_round)
    if not bsd_round:
        return None
    candidates = round_events.get(bsd_round, [])
    idx = int(bracket_order) - 1
    if 0 <= idx < len(candidates):
        return candidates[idx]
    return None


def link_matches_to_bsd(db: Session, client: BsdClient | None = None, *, apply: bool = True) -> dict:
    client = client or BsdClient()
    if not client.configured:
        return {"linked": 0, "total": 0, "unmatched": [], "error": "BSD_API_KEY not configured"}

    bsd_events = client.get_all_worldcup_events()
    round_events = _group_events_by_round(bsd_events)
    group_events = [e for e in bsd_events if e.get("group_name")]

    matches = list(db.scalars(select(Match)).all())
    linked = 0
    unmatched: list[dict] = []

    for match in matches:
        if match.round_type == "knockout" or match.bracket_round:
            event = _match_knockout(match, round_events)
        else:
            event = _match_group_stage(match, group_events)

        if not event:
            unmatched.append({
                "id": match.id,
                "team1": match.team1_name,
                "team2": match.team2_name,
                "group": match.group_name,
                "bracket_round": match.bracket_round,
                "bracket_order": match.bracket_order,
            })
            continue

        if apply:
            match.external_fixture_id = event["id"]
            match.external_provider = "bsd"
        linked += 1

    if apply:
        db.commit()

    return {
        "linked": linked,
        "total": len(matches),
        "unmatched": unmatched,
        "bsd_events": len(bsd_events),
    }
