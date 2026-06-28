#!/usr/bin/env python3
"""Smoke checklist: key API surfaces for production / staging validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="WC2026 API smoke checklist")
    parser.add_argument("--base", default="http://127.0.0.1:10086", help="API base URL")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    checks: list[tuple[str, str, int]] = [
        ("health", f"{base}/api/health", 200),
        ("schedule", f"{base}/api/schedule/matches?limit=1", 200),
        ("shop products", f"{base}/api/shop/products", 200),
        ("season narrative", f"{base}/api/game/season-narrative", 401),
        ("widget predict", f"{base}/api/widget/predict", 200),
    ]
    failed = 0
    print(f"=== Smoke: {base} ===")
    with httpx.Client(timeout=15.0) as client:
        for name, url, expect in checks:
            try:
                r = client.get(url)
                ok = r.status_code == expect
                mark = "OK" if ok else "FAIL"
                print(f"  [{mark}] {name}: {r.status_code} (expected {expect})")
                if not ok:
                    failed += 1
            except Exception as exc:
                print(f"  [FAIL] {name}: {exc}")
                failed += 1
    if failed:
        print(f"\nResult: FAIL ({failed} checks)")
        return 1
    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
