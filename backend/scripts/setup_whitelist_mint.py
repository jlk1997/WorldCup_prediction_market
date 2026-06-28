#!/usr/bin/env python3
"""生产 env 切换 + 首场 RMB 打新 whitelist 内测准备脚本。"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.services.primary_mint_service import PrimaryMintService  # noqa: E402


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def main() -> int:
    parser = argparse.ArgumentParser(description="创建 whitelist 内测打新活动")
    parser.add_argument("--card-code", required=True, help="CollectibleCard.code")
    parser.add_argument("--name", default="内测 whitelist 打新")
    parser.add_argument("--supply", type=int, default=50)
    parser.add_argument("--price-fen", type=int, default=6800)
    parser.add_argument("--user-ids", default="", help="逗号分隔用户 ID，写入 whitelist 预约")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        svc = PrimaryMintService(db)
        now = _utcnow()
        payload = {
            "code": f"whitelist_{now.strftime('%Y%m%d_%H%M')}",
            "name": args.name,
            "card_code": args.card_code,
            "total_supply": args.supply,
            "currency": "rmb",
            "price_fen": args.price_fen,
            "sale_mode": "whitelist",
            "starts_at": now,
            "ends_at": now + timedelta(days=7),
            "status": "live",
        }
        ev = svc.admin_create_event(payload)
        event_id = ev["id"]
        if args.user_ids.strip():
            from app.db.models.commerce import MintReservation

            for uid in args.user_ids.split(","):
                uid = uid.strip()
                if not uid.isdigit():
                    continue
                db.add(
                    MintReservation(
                        event_id=event_id,
                        user_id=int(uid),
                        status="won",
                    )
                )
        db.commit()
        print(f"OK: mint event id={event_id} code={payload['code']}")
        print("下一步: PRODUCTION_MODE=true ALIPAY_MOCK=false 后运行 check_production_readiness.py")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
