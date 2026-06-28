"""Resolve knockout placeholders from group standings and match results."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DataSyncLog, Match
from app.services.bracket_templates import (
    build_bracket_meta_for_knockout,
    build_r32_pairings,
    is_placeholder_name,
    match_loser_name,
    match_winner_name,
)
from app.services.group_standings import (
    all_group_stage_done,
    build_standings,
    rank_third_place_teams,
    tables_to_dict,
)

logger = logging.getLogger(__name__)


class KnockoutResolverService:
    def __init__(self, db: Session):
        self.db = db

    def get_group_matches(self) -> list[Match]:
        stmt = select(Match).where(Match.round_type == "group")
        return list(self.db.scalars(stmt).all())

    def get_knockout_matches(self) -> list[Match]:
        stmt = select(Match).where(Match.round_type == "knockout").order_by(Match.id)
        return list(self.db.scalars(stmt).all())

    def get_standings_payload(self) -> dict:
        tables = build_standings(self.get_group_matches())
        return tables_to_dict(tables)

    def _index_knockout(self, matches: list[Match]) -> dict[tuple[str, int], Match]:
        idx: dict[tuple[str, int], Match] = {}
        for m in matches:
            if m.bracket_round and m.bracket_order:
                idx[(m.bracket_round, m.bracket_order)] = m
        return idx

    def _resolve_feed(self, feed: dict, idx: dict[tuple[str, int], Match]) -> str | None:
        rnd = feed.get("round")
        order = feed.get("order")
        if not rnd or not order:
            return None
        src = idx.get((rnd, order))
        if not src:
            return None
        if feed.get("loser"):
            return match_loser_name(src)
        return match_winner_name(src)

    def resolve(self) -> dict:
        group_matches = self.get_group_matches()
        knockout_matches = self.get_knockout_matches()
        tables = build_standings(group_matches)
        third_teams = rank_third_place_teams(tables)
        groups_done = all_group_stage_done(tables)

        updated = 0
        idx = self._index_knockout(knockout_matches)
        default_meta = build_bracket_meta_for_knockout()

        # Ensure bracket_meta exists on knockout rows
        for m in knockout_matches:
            key = (m.bracket_round, m.bracket_order)
            if key in default_meta and not m.bracket_meta:
                m.bracket_meta = default_meta[key]

        # R32 from completed group tables (+ thirds when known) — only before BSD link.
        pairs = build_r32_pairings(tables, third_teams, require_full=groups_done)
        if not pairs and groups_done:
            pairs = build_r32_pairings(tables, third_teams, require_full=False)
        for i, (t1, t2) in enumerate(pairs, 1):
            m = idx.get(("r32", i))
            if not m:
                continue
            if m.external_fixture_id:
                continue
            changed = False
            if is_placeholder_name(m.team1_name) or m.team1_name != t1:
                m.team1_name = t1
                changed = True
            if is_placeholder_name(m.team2_name) or m.team2_name != t2:
                m.team2_name = t2
                changed = True
            if changed:
                updated += 1

        # Later rounds from winners/losers
        for rnd in ("r16", "qf", "sf", "final", "third"):
            count = {"r16": 8, "qf": 4, "sf": 2, "final": 1, "third": 1}[rnd]
            for order in range(1, count + 1):
                m = idx.get((rnd, order))
                if not m or not m.bracket_meta:
                    continue
                meta = m.bracket_meta
                home_feed = meta.get("home_feed")
                away_feed = meta.get("away_feed")
                if home_feed:
                    resolved = self._resolve_feed(home_feed, idx)
                    if resolved and (is_placeholder_name(m.team1_name) or resolved != m.team1_name):
                        m.team1_name = resolved
                        updated += 1
                if away_feed:
                    resolved = self._resolve_feed(away_feed, idx)
                    if resolved and (is_placeholder_name(m.team2_name) or resolved != m.team2_name):
                        m.team2_name = resolved
                        updated += 1

        self.db.add(
            DataSyncLog(
                source="knockout_resolver",
                status="ok",
                records=updated,
            )
        )
        self.db.commit()

        return {
            "updated": updated,
            "groups_complete": groups_done,
            "third_qualifiers": third_teams,
            "standings": tables_to_dict(tables),
        }
