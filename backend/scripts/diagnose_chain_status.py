#!/usr/bin/env python3
"""文昌链 / AVATA 线上诊断：env、DB 分布、ingest 依赖项。"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def main() -> int:
    s = get_settings()
    print("=== WC2026 文昌链诊断 ===\n")
    print("环境")
    print(f"  AVATA_ENABLED={s.avata_enabled}")
    print(f"  AVATA_MOCK={s.avata_mock}")
    print(f"  avata_active={s.avata_active}")
    print(f"  AVATA_NFT_CLASS_ID={'set' if s.avata_nft_class_id else 'unset'}")
    print(f"  AVATA_CLASS_OWNER={'set' if s.avata_class_owner else 'unset'}")
    print(f"  PUBLIC_API_BASE_URL={s.public_api_base_url or '(unset)'}")
    print(f"  ENABLE_BACKGROUND_INGEST={s.enable_background_ingest}")
    print(f"  REDIS_URL={'set' if (s.redis_url or '').strip() else 'unset'}")

    if s.avata_enabled and not s.public_api_base_url:
        print("\n  [错误] AVATA 已启用但 PUBLIC_API_BASE_URL 未设置")
    if s.avata_enabled and not s.avata_mock and not s.avata_configured:
        print("\n  [错误] AVATA_MOCK=false 但 API Key/Secret 未配置")

    db = SessionLocal()
    try:
        print("\n卡牌 chain_status 分布")
        rows = db.execute(
            text(
                "SELECT COALESCE(chain_status, 'none') AS st, COUNT(*) AS cnt "
                "FROM user_collectible_cards GROUP BY 1 ORDER BY cnt DESC"
            )
        ).fetchall()
        for st, cnt in rows:
            print(f"  {st}: {cnt}")

        print("\n失败原因 Top 5")
        err_rows = db.execute(
            text(
                "SELECT COALESCE(chain_error, '(empty)') AS err, COUNT(*) AS cnt "
                "FROM user_collectible_cards WHERE chain_status = 'failed' "
                "GROUP BY 1 ORDER BY cnt DESC LIMIT 5"
            )
        ).fetchall()
        if err_rows:
            for err, cnt in err_rows:
                print(f"  {err[:80]}: {cnt}")
        else:
            print("  (无 failed 记录)")

        from app.db.models.commerce import UserChainAccount, UserCollectibleCard

        no_addr = (
            db.query(func.count(UserChainAccount.id))
            .filter(UserChainAccount.native_address.is_(None))
            .scalar()
            or 0
        )
        print(f"\n链账户无地址: {no_addr}")

        none_count = (
            db.query(func.count(UserCollectibleCard.id))
            .filter(
                (UserCollectibleCard.chain_status.is_(None))
                | (UserCollectibleCard.chain_status == "none")
            )
            .scalar()
            or 0
        )
        print(f"chain_status=none 卡牌: {none_count}")
        if s.avata_active and none_count:
            print("  → 可运行: python scripts/backfill_chain_mint.py --dry-run")

        pending = (
            db.query(func.count(UserCollectibleCard.id))
            .filter(UserCollectibleCard.chain_status.in_(("pending", "minting")))
            .scalar()
            or 0
        )
        print(f"pending/minting 积压: {pending}")
        if pending and not s.enable_background_ingest:
            print("  → 警告: ENABLE_BACKGROUND_INGEST=false，须独立 ingest 进程处理队列")

        sample = (
            db.query(UserCollectibleCard.id)
            .filter(UserCollectibleCard.chain_status == "minted")
            .order_by(UserCollectibleCard.id.desc())
            .first()
        )
        if sample and s.public_api_base_url:
            base = s.public_api_base_url.rstrip("/")
            print(f"\n元数据样例 URL: {base}/api/collectible/metadata/{sample[0]}.json")
    finally:
        db.close()

    print("\n建议 API 抽测（登录后）: GET /api/collectible/chain/status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
