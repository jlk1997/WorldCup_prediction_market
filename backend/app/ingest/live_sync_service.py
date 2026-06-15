"""Sync live match data from BSD into PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DataSyncLog, Match
from app.core.match_scores import scores_for_team1_team2
from app.ingest.bsd_adapter import InternalFixture, event_to_internal
from app.ingest.bsd_client import BsdClient
from app.ingest.bsd_event_parser import normalize_bsd_incidents
from app.ingest.bsd_link_service import link_matches_to_bsd
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

        updated = 0
        updated_external_ids: set[str] = set()
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
                updated += 1
                if fixture.external_id:
                    updated_external_ids.add(fixture.external_id)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        near_start = now - timedelta(hours=6)
        near_end = now + timedelta(hours=48)

        for match in matches:
            if not match.external_fixture_id or match.external_fixture_id in updated_external_ids:
                continue
            if match.status == "live":
                continue
            md = match.match_date
            if match.status == "scheduled":
                if md and (md < near_start or md > near_end):
                    continue
            elif match.status == "finished":
                if md and md < now - timedelta(hours=24):
                    continue
            else:
                continue
            event = self.client.get_event(match.external_fixture_id)
            if not event:
                continue
            fixture = event_to_internal(event)
            if _apply_internal_fixture(match, fixture, self.client):
                updated += 1

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
