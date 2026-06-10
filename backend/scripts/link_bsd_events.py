"""Link local 104 matches to BSD event IDs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.ingest.bsd_link_service import link_matches_to_bsd


def main():
    parser = argparse.ArgumentParser(description="Link matches to BSD events")
    parser.add_argument("--apply", action="store_true", help="Write links to database")
    parser.add_argument("--dry-run", action="store_true", help="Report only (default)")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    db = SessionLocal()
    try:
        result = link_matches_to_bsd(db, apply=apply)
        print(f"Linked {result['linked']}/{result['total']} (BSD events: {result.get('bsd_events')})")
        if result.get("error"):
            print("Error:", result["error"])
            sys.exit(1)
        unmatched = result.get("unmatched") or []
        if unmatched:
            print(f"Unmatched ({len(unmatched)}):")
            for item in unmatched[:20]:
                print(f"  #{item['id']} {item['team1']} vs {item['team2']} ({item.get('group')})")
            if len(unmatched) > 20:
                print(f"  ... and {len(unmatched) - 20} more")
        if apply and result["linked"] < result["total"]:
            sys.exit(2)
    finally:
        db.close()


if __name__ == "__main__":
    main()
