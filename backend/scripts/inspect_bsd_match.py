"""Print BSD event state for local match rows (debug stale scheduled scores)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import or_, select

from app.core.match_kickoff import parse_kickoff
from app.db.models import Match
from app.db.models.commerce import GamePrediction
from app.db.session import SessionLocal
from app.ingest.bsd_adapter import event_to_internal, resolve_event_status, team_pair_key
from app.ingest.bsd_client import BsdClient
from app.ingest.bsd_link_service import list_group_event_candidates, pick_best_bsd_event


def _print_pending_predictions(db) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = (
        db.query(GamePrediction, Match)
        .join(Match, GamePrediction.match_id == Match.id)
        .filter(GamePrediction.status == "pending")
        .order_by(GamePrediction.created_at.desc())
        .limit(50)
        .all()
    )
    print(f"\n=== Pending predictions ({len(rows)} shown) ===")
    for pred, m in rows:
        kick = parse_kickoff(m)
        age_txt = f"{age_h:.1f}" if age_h is not None else "?"
        print(
            f"  pred#{pred.id} user={pred.user_id} match#{m.id} {m.team1_name} vs {m.team2_name} "
            f"match_status={m.status} score={m.home_score}:{m.away_score} "
            f"kick={kick} ext={m.external_fixture_id} age_h={age_txt}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect BSD linkage for local matches")
    parser.add_argument("--match-id", type=int, action="append", help="Local match id (repeatable)")
    parser.add_argument("--team", type=str, help="Filter by team name substring")
    parser.add_argument("--stale-only", action="store_true", help="Only scheduled past kickoff")
    parser.add_argument("--pending-predictions", action="store_true", help="List pending predictions")
    args = parser.parse_args()

    if args.pending_predictions:
        with SessionLocal() as db:
            _print_pending_predictions(db)
        if not args.match_id and not args.team and not args.stale_only:
            return 0

    client = BsdClient()
    if not client.configured:
        print("BSD_API_KEY not configured", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        q = select(Match)
        if args.match_id:
            q = q.where(Match.id.in_(args.match_id))
        if args.team:
            t = f"%{args.team}%"
            q = q.where(or_(Match.team1_name.like(t), Match.team2_name.like(t)))
        matches = list(db.scalars(q.order_by(Match.match_date)).all())

    league = client.list_league_events(date_from="2026-06-01", date_to="2026-06-20")
    group_events = [e for e in league if e.get("group_name")]

    for m in matches:
        if args.stale_only and m.status != "scheduled":
            continue
        ext = m.external_fixture_id
        print(f"\n=== Match #{m.id} {m.team1_name} vs {m.team2_name} ===")
        print(f"  local: status={m.status} score={m.home_score}:{m.away_score} kick={m.match_date} ext={ext}")
        if ext:
            ev = client.get_event(int(ext))
            if ev:
                fx = event_to_internal(ev)
                print(
                    f"  linked BSD #{ext}: status={resolve_event_status(ev)} "
                    f"score={fx.home_score}:{fx.away_score} date={ev.get('event_date')}"
                )
            else:
                print(f"  linked BSD #{ext}: GET failed")
        candidates = list_group_event_candidates(m, group_events)
        print(f"  candidates ({len(candidates)}): pair={team_pair_key(m.team1_name, m.team2_name)}")
        for c in candidates:
            cid = c.get("id")
            full = client.get_event(int(cid)) if cid else c
            st = resolve_event_status(full or c)
            print(f"    - BSD #{cid} status={st} date={(full or c).get('event_date')}")
        best = pick_best_bsd_event(m, [client.get_event(int(c["id"])) or c for c in candidates if c.get("id")])
        if best:
            print(f"  pick_best -> BSD #{best.get('id')} status={resolve_event_status(best)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
