"""Link local Match rows to BSD event IDs."""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.bsd_team_names import normalize_group_label
from app.db.models import Match
from app.ingest.bsd_adapter import LOCAL_BRACKET_TO_BSD_ROUND, team_pair_key
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


def _match_group_stage(local: Match, bsd_events: list[dict]) -> dict | None:
    local_group = normalize_group_label(local.group_name)
    pair = team_pair_key(local.team1_name, local.team2_name)
    if not local_group or not pair:
        return None
    for event in bsd_events:
        if normalize_group_label(event.get("group_name")) != local_group:
            continue
        from app.ingest.bsd_adapter import event_to_internal

        internal = event_to_internal(event)
        event_pair = team_pair_key(internal.home_name, internal.away_name)
        if event_pair and event_pair == pair:
            return event
    return None


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
