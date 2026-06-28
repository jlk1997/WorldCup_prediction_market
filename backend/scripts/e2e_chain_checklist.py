#!/usr/bin/env python3
"""文昌链 E2E 冒烟：metadata 公开、chain/status、诊断脚本入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=None, help="API base e.g. https://loveaibaby.cn")
    parser.add_argument("--user-card-id", type=int, default=None, help="Sample minted user_card_id")
    args = parser.parse_args()

    s = get_settings()
    base = (args.base or s.public_api_base_url or f"http://127.0.0.1:{s.backend_port}").rstrip("/")
    print(f"=== Chain E2E smoke @ {base} ===\n")

    checks: list[tuple[str, bool, str]] = []

    if args.user_card_id:
        url = f"{base}/api/collectible/metadata/{args.user_card_id}.json"
        try:
            r = httpx.get(url, timeout=15)
            ok = r.status_code == 200 and "name" in r.json()
            checks.append(("metadata public", ok, f"{r.status_code} {url}"))
        except Exception as exc:
            checks.append(("metadata public", False, str(exc)))
    else:
        checks.append(("metadata public", True, "skipped (pass --user-card-id)"))

    health_url = f"{base}/api/health"
    try:
        r = httpx.get(health_url, timeout=10)
        checks.append(("api health", r.status_code == 200, str(r.status_code)))
    except Exception as exc:
        checks.append(("api health", False, str(exc)))

    print("Config")
    print(f"  avata_active={s.avata_active}")
    print(f"  PUBLIC_API_BASE_URL={s.public_api_base_url or '(unset)'}")

    print("\nChecks")
    failed = 0
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        print(f"  [{mark}] {name}: {detail}")

    print("\nManual (login required):")
    print("  GET /api/collectible/chain/status")
    print("  POST /api/collectible/chain/retry/{user_card_id}")
    print("  GET /api/collectible/user-card/{id}/provenance")
    print("\nOps:")
    print("  python scripts/diagnose_chain_status.py")
    print("  python scripts/backfill_chain_mint.py --dry-run")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
