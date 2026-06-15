"""Sync live match data from BSD into PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DataSyncLog, Match
from app.core.match_kickoff import parse_kickoff
from app.core.match_scores import scores_for_team1_team2
from app.ingest.bsd_adapter import InternalFixture, event_to_internal
from app.ingest.bsd_client import BsdClient
from app.ingest.bsd_event_parser import normalize_bsd_incidents
from app.ingest.bsd_link_service import link_matches_to_bsd, list_group_event_candidates, pick_best_bsd_event
from app.ingest.quota import invalidate_live_cache

logger = logging.getLogger(__name__)


def _apply_internal_fixture(
    match: Match,
    fixture: InternalFixture,
    client: BsdClient | None = None,
) -> bool:
    if not fixture.external_id:
        return False
    if match.external_fixture_id and fixture.external_id != match.external_fixture_id:
        return False
    if not match.external_fixture_id:
        return False

    match.status = fixture.status
    t1_score, t2_score = scores_for_team1_team2(
        match.team1_name,
        match.team2_name,
        fixture.home_name,
        fixture.away_name,
        fixture.home_score,
        fixture.away_score,
    )
    match.home_score = t1_score
    match.away_score = t2_score
    match.minute = fixture.minute
    match.period = fixture.period
    match.external_fixture_id = fixture.external_id
    match.external_provider = fixture.provider
    match.live_updated_at = datetime.now(timezone.utc)

    if fixture.event_date and not match.match_date:
        match.match_date = fixture.event_date
    if fixture.venue and not match.stadium:
        match.stadium = fixture.venue

    if client and fixture.external_id and match.status in ("live", "finished"):
        raw_events = client.get_incidents(fixture.external_id)
        if raw_events:
            match.events_json = normalize_bsd_incidents(raw_events)

    return True


def _should_poll_match(
    match: Match,
    now: datetime,
    near_end: datetime,
) -> bool:
    """Whether to fetch BSD for a linked match outside the live feed."""
    kick = parse_kickoff(match)
    if match.status == "live":
        return True
    if match.status == "scheduled":
        if kick is None:
            return True
        # Past kickoff but still marked scheduled — must catch up (e.g. after ingest outage).
        if kick <= now:
            return True
        return kick <= near_end
    if match.status == "finished":
        if kick is None:
            return False
        return kick >= now - timedelta(hours=24)
    return False


def _sync_events_batch(
    client: BsdClient,
    matches_by_external_id: dict[int, Match],
    updated_external_ids: set[int],
    *,
    date_from: str,
    date_to: str,
) -> tuple[int, list[dict]]:
    """Bulk-update linked matches from league events list (fewer API calls than per-event GET)."""
    events = client.list_league_events(date_from=date_from, date_to=date_to)
    updated = 0
    for event in events:
        fixture = event_to_internal(event)
        eid = fixture.external_id
        if not eid or eid in updated_external_ids:
            continue
        match = matches_by_external_id.get(eid)
        if match and _apply_internal_fixture(match, fixture, client):
            updated += 1
            updated_external_ids.add(eid)
    return updated, events


def _reconcile_stale_matches(
    matches: list[Match],
    group_events: list[dict],
    now: datetime,
    client: BsdClient,
    updated_external_ids: set[int],
) -> int:
    """Re-link or refresh matches that should have started but are still scheduled locally."""
    updated = 0
    for match in matches:
        if match.status != "scheduled" or not match.external_fixture_id:
            continue
        kick = parse_kickoff(match)
        if not kick or kick > now:
            continue
        candidates = list_group_event_candidates(match, group_events)
        best = pick_best_bsd_event(match, candidates)
        if not best:
            continue
        best_id = int(best["id"])
        fixture = event_to_internal(best)
        if best_id != match.external_fixture_id:
            if fixture.status not in ("finished", "live") and fixture.home_score is None:
                continue
            logger.info(
                "Re-link stale match #%s %s vs %s: %s -> %s (%s)",
                match.id,
                match.team1_name,
                match.team2_name,
                match.external_fixture_id,
                best_id,
                fixture.status,
            )
            match.external_fixture_id = best_id
            match.external_provider = "bsd"
        if best_id in updated_external_ids:
            continue
        if _apply_internal_fixture(match, fixture, client):
            updated += 1
            updated_external_ids.add(best_id)
    return updated


class LiveMatchSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.client = BsdClient()

    def sync(self) -> int:
        if not self.client.configured:
            self._log("bsd", "skipped", 0, "BSD_API_KEY not configured")
            return 0

        unlinked = self.db.scalar(
            select(func.count()).select_from(Match).where(Match.external_fixture_id.is_(None))
        ) or 0
        if unlinked:
            linked = self.link_fixtures()
            logger.info(
                "Auto BSD link: %s/%s matches linked (%s still unmapped)",
                linked,
                unlinked,
                max(0, unlinked - linked),
            )

        live_feed = 0
        updated = 0
        updated_external_ids: set[int] = set()
        matches = list(
            self.db.scalars(
                select(Match).where(Match.external_fixture_id.isnot(None))
            ).all()
        )
        by_external_id = {m.external_fixture_id: m for m in matches if m.external_fixture_id}

        for event in self.client.get_live_events():
            fixture = event_to_internal(event)
            match = by_external_id.get(fixture.external_id)
            if match and _apply_internal_fixture(match, fixture, self.client):
                live_feed += 1
                updated += 1
                if fixture.external_id:
                    updated_external_ids.add(fixture.external_id)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        near_end = now + timedelta(hours=48)
        bulk_from = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        bulk_to = (now + timedelta(days=2)).strftime("%Y-%m-%d")
        bulk_updated, league_events = _sync_events_batch(
            self.client,
            by_external_id,
            updated_external_ids,
            date_from=bulk_from,
            date_to=bulk_to,
        )
        updated += bulk_updated

        group_events = [e for e in league_events if e.get("group_name")]
        reconciled = _reconcile_stale_matches(
            matches,
            group_events,
            now,
            self.client,
            updated_external_ids,
        )
        updated += reconciled

        stale_scheduled = sum(
            1
            for m in matches
            if m.status == "scheduled"
            and m.external_fixture_id
            and (kick := parse_kickoff(m)) is not None
            and kick <= now
        )
        if stale_scheduled:
            logger.info("BSD catch-up: %s scheduled matches past kickoff", stale_scheduled)

        individual = 0
        for match in matches:
            if not match.external_fixture_id or match.external_fixture_id in updated_external_ids:
                continue
            if not _should_poll_match(match, now, near_end):
                continue
            event = self.client.get_event(match.external_fixture_id)
            if not event:
                continue
            fixture = event_to_internal(event)
            if _apply_internal_fixture(match, fixture, self.client):
                updated += 1
                individual += 1

        if live_feed or bulk_updated or reconciled or individual:
            logger.info(
                "BSD sync breakdown: live_feed=%s bulk=%s reconcile=%s individual=%s total=%s",
                live_feed,
                bulk_updated,
                reconciled,
                individual,
                updated,
            )

        self.db.commit()
        invalidate_live_cache()
        try:
            from app.core.cache import cache_delete

            cache_delete("stats:overview")
            cache_delete("schedule:all")
            cache_delete("schedule:bracket")
            cache_delete("schedule:standings:local")
        except Exception:
            pass
        try:
            from app.services.knockout_resolver import KnockoutResolverService

            KnockoutResolverService(self.db).resolve()
        except Exception as exc:
            logger.warning("Knockout bracket resolve skipped: %s", exc)
        self._log("bsd", "ok", updated)
        return updated

    def link_fixtures(self) -> int:
        """Link local matches to BSD event IDs without inserting new rows."""
        if not self.client.configured:
            self._log("bsd_link", "skipped", 0, "BSD_API_KEY not configured")
            return 0

        result = link_matches_to_bsd(self.db, self.client, apply=True)
        invalidate_live_cache()
        linked = int(result.get("linked") or 0)
        error = None
        if linked < int(result.get("total") or 0):
            error = f"{len(result.get('unmatched') or [])} matches unmatched"
        self._log("bsd_link", "ok" if not error else "partial", linked, error)
        return linked

    def import_fixtures(self, max_matches: int = 104) -> int:
        """Backward-compatible alias for link_fixtures."""
        return self.link_fixtures()

    def _log(self, source: str, status: str, records: int, error: str | None = None):
        self.db.add(DataSyncLog(source=source, status=status, records=records, error=error))
        self.db.commit()
