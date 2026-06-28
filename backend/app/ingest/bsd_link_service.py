"""Link local Match rows to BSD event IDs."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.bsd_team_names import normalize_group_label
from app.db.models import Match
from app.core.match_kickoff import parse_kickoff, parse_match_kickoff
from app.ingest.bsd_adapter import LOCAL_BRACKET_TO_BSD_ROUND, event_to_internal, team_pair_key
from app.ingest.bsd_client import BsdClient
from app.services.bracket_templates import is_placeholder_name

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


def apply_bsd_schedule_to_match(match: Match, event: dict) -> bool:
    """Overwrite local placeholder kickoff with BSD authoritative schedule."""
    fixture = event_to_internal(event)
    changed = False
    if fixture.local_date and match.match_date != fixture.local_date:
        match.match_date = fixture.local_date
        changed = True
    if fixture.local_time and match.match_time != fixture.local_time:
        match.match_time = fixture.local_time
        changed = True
    if fixture.venue and match.stadium != fixture.venue:
        match.stadium = fixture.venue
        changed = True
    return changed


def pick_best_bsd_event(local: Match, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    local_kick = parse_kickoff(local)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    kick_passed = bool(local_kick and local_kick <= now)

    finished_live = [
        e
        for e in candidates
        if event_to_internal(e).status in ("finished", "live")
    ]
    if kick_passed and finished_live:
        candidates = finished_live

    def rank(event: dict) -> tuple:
        internal = event_to_internal(event)
        status_rank = {"finished": 0, "live": 1, "scheduled": 2}.get(internal.status, 3)
        kick = _bsd_event_kickoff(event)
        kick_ts = kick.timestamp() if kick else 9999999999.0
        has_score = 0 if internal.home_score is not None and internal.away_score is not None else 1
        return (status_rank, has_score, kick_ts, int(event.get("id") or 0))

    return min(candidates, key=rank)


def _match_group_stage(local: Match, bsd_events: list[dict]) -> dict | None:
    candidates = list_group_event_candidates(local, bsd_events)
    return pick_best_bsd_event(local, candidates)


def list_knockout_event_candidates(
    local: Match,
    round_events: dict[str, list[dict]],
) -> list[dict]:
    """BSD knockout events that match local team pair within the same bracket round."""
    bracket_round = local.bracket_round
    if not bracket_round:
        return []
    bsd_round = LOCAL_BRACKET_TO_BSD_ROUND.get(bracket_round)
    if not bsd_round:
        return []
    pair = team_pair_key(local.team1_name, local.team2_name)
    if not pair or is_placeholder_name(local.team1_name) or is_placeholder_name(local.team2_name):
        return []
    out: list[dict] = []
    for event in round_events.get(bsd_round, []):
        internal = event_to_internal(event)
        event_pair = team_pair_key(internal.home_name, internal.away_name)
        if event_pair and event_pair == pair:
            out.append(event)
    return out


def _match_knockout(local: Match, round_events: dict[str, list[dict]]) -> dict | None:
    bracket_round = local.bracket_round
    bracket_order = local.bracket_order
    if not bracket_round:
        return None
    candidates = list_knockout_event_candidates(local, round_events)
    if candidates:
        return pick_best_bsd_event(local, candidates)
    # Placeholder teams: fall back to bracket_order index in BSD round list.
    if not bracket_order:
        return None
    bsd_round = LOCAL_BRACKET_TO_BSD_ROUND.get(bracket_round)
    if not bsd_round:
        return None
    candidates = round_events.get(bsd_round, [])
    idx = int(bracket_order) - 1
    if 0 <= idx < len(candidates):
        return candidates[idx]
    return None


def relink_mismatched_knockout_matches(
    matches: list[Match],
    bsd_events: list[dict],
    client: BsdClient | None = None,
) -> int:
    """Fix knockout rows linked by bracket index to the wrong BSD event."""
    round_events = _group_events_by_round(bsd_events)
    by_id = {int(e["id"]): e for e in bsd_events if e.get("id")}
    relinked = 0
    for match in matches:
        if not match.bracket_round:
            continue
        if is_placeholder_name(match.team1_name) or is_placeholder_name(match.team2_name):
            continue
        pair = team_pair_key(match.team1_name, match.team2_name)
        if not pair:
            continue
        current = by_id.get(int(match.external_fixture_id or 0))
        if current:
            internal = event_to_internal(current)
            event_pair = team_pair_key(internal.home_name, internal.away_name)
            if event_pair and event_pair == pair:
                continue
        candidates = list_knockout_event_candidates(match, round_events)
        if not candidates and client:
            candidates = _refresh_bsd_knockout_candidates(match, round_events, client)
        best = pick_best_bsd_event(match, candidates)
        if not best:
            continue
        best_id = int(best["id"])
        if best_id == int(match.external_fixture_id or 0):
            continue
        logger.info(
            "Re-link knockout #%s %s vs %s: %s -> %s",
            match.id,
            match.team1_name,
            match.team2_name,
            match.external_fixture_id,
            best_id,
        )
        match.external_fixture_id = best_id
        match.external_provider = "bsd"
        apply_bsd_schedule_to_match(match, best)
        relinked += 1
    return relinked


def _refresh_bsd_knockout_candidates(
    match: Match,
    round_events: dict[str, list[dict]],
    client: BsdClient,
) -> list[dict]:
    """Re-fetch BSD round events when catalog summaries omit team names."""
    bracket_round = match.bracket_round
    if not bracket_round:
        return []
    bsd_round = LOCAL_BRACKET_TO_BSD_ROUND.get(bracket_round)
    if not bsd_round:
        return []
    refreshed: list[dict] = []
    for event in round_events.get(bsd_round, []):
        eid = event.get("id")
        if not eid:
            continue
        full = client.get_event(int(eid)) or event
        refreshed.append(full)
    return list_knockout_event_candidates(match, _group_events_by_round(refreshed))


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
            apply_bsd_schedule_to_match(match, event)
        linked += 1

    if apply:
        db.commit()

    return {
        "linked": linked,
        "total": len(matches),
        "unmatched": unmatched,
        "bsd_events": len(bsd_events),
    }
