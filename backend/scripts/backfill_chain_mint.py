#!/usr/bin/env python3
"""历史卡牌补排队铸造：chain_status none → pending（须 AVATA 已启用）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import or_  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.models.commerce import UserCollectibleCard  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.collectible_chain_service import CHAIN_STATUS_PENDING  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill chain mint queue for legacy cards")
    parser.add_argument("--dry-run", action="store_true", help="Only count, do not update")
    parser.add_argument("--limit", type=int, default=500, help="Max rows per run")
    parser.add_argument("--user-id", type=int, default=None, help="Only this user")
    args = parser.parse_args()

    s = get_settings()
    if not s.avata_active:
        print("AVATA 未激活 (AVATA_ENABLED + keys/mock)。中止。")
        return 1

    db = SessionLocal()
    try:
        q = db.query(UserCollectibleCard).filter(
            or_(UserCollectibleCard.chain_status.is_(None), UserCollectibleCard.chain_status == "none")
        )
        if args.user_id:
            q = q.filter(UserCollectibleCard.user_id == args.user_id)
        rows = q.order_by(UserCollectibleCard.id.asc()).limit(max(1, args.limit)).all()
        print(f"待补铸: {len(rows)} 张 (limit={args.limit})")
        if args.dry_run:
            return 0
        updated = 0
        for row in rows:
            row.chain_status = CHAIN_STATUS_PENDING
            row.chain_error = None
            row.chain_operation_id = None
            updated += 1
        db.commit()
        print(f"已设为 pending: {updated} 张。等待 ingest scheduler process_pending。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
