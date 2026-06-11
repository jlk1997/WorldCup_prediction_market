#!/usr/bin/env python3
"""Benchmark key API endpoints on localhost (for ingest spike diagnosis)."""

from __future__ import annotations

import argparse
import statistics
import time
import urllib.error
import urllib.request


def fetch(url: str, timeout: float = 10.0) -> float:
    start = time.perf_counter()
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        resp.read()
    return time.perf_counter() - start


def bench(url: str, rounds: int, sleep_sec: float) -> list[float]:
    times: list[float] = []
    for i in range(rounds):
        try:
            times.append(fetch(url))
        except urllib.error.URLError as exc:
            print(f"  [{i + 1}/{rounds}] ERROR: {exc}")
        if sleep_sec > 0 and i + 1 < rounds:
            time.sleep(sleep_sec)
    return times


def summarize(label: str, times: list[float]) -> None:
    if not times:
        print(f"{label}: no successful samples")
        return
    print(
        f"{label}: n={len(times)} "
        f"min={min(times)*1000:.1f}ms "
        f"p50={statistics.median(times)*1000:.1f}ms "
        f"max={max(times)*1000:.1f}ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bench WC2026 API endpoints")
    parser.add_argument("--base", default="http://127.0.0.1:10086", help="API base URL")
    parser.add_argument("--rounds", type=int, default=5, help="Requests per endpoint")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds between requests")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    endpoints = [
        ("health", f"{base}/health"),
        ("stats/overview", f"{base}/api/stats/overview"),
        ("schedule", f"{base}/api/schedule"),
        ("live/matches", f"{base}/api/live/matches"),
    ]

    print(f"Benchmark base={base} rounds={args.rounds} sleep={args.sleep}s")
    for label, url in endpoints:
        print(f"\n--- {label} ---")
        times = bench(url, args.rounds, args.sleep)
        summarize(label, times)


if __name__ == "__main__":
    main()
