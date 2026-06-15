"""One-shot repair: overwrite placeholder match dates/times from BSD events."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db.models import Match
from app.db.session import SessionLocal
from app.ingest.bsd_client import BsdClient
from app.ingest.bsd_link_service import apply_bsd_schedule_to_match
from app.ingest.quota import invalidate_live_cache
from app.core.match_cache import invalidate_match_caches


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync match kickoff times from BSD")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without saving")
    args = parser.parse_args()

    client = BsdClient()
    if not client.configured:
        print("BSD_API_KEY not configured", file=sys.stderr)
        return 1

    events = client.get_all_worldcup_events()
    by_id = {int(e["id"]): e for e in events if e.get("id")}
    print(f"Loaded {len(by_id)} BSD events")

    db = SessionLocal()
    try:
        matches = list(db.scalars(select(Match).where(Match.external_fixture_id.isnot(None))).all())
        updated = 0
        for m in matches:
            ev = by_id.get(int(m.external_fixture_id or 0))
            if not ev:
                continue
            before = (m.match_date, m.match_time, m.stadium)
            if apply_bsd_schedule_to_match(m, ev):
                after = (m.match_date, m.match_time, m.stadium)
                print(f"  #{m.id} {m.team1_name} vs {m.team2_name}: {before} -> {after}")
                updated += 1
        if args.dry_run:
            db.rollback()
            print(f"Dry run: would update {updated} matches")
        else:
            db.commit()
            invalidate_match_caches()
            print(f"Updated {updated} matches")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
