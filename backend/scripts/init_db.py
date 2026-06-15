"""Initialize database schema and seed base data."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from app.core.config import get_settings
from app.db.models import Match
from app.db.session import SessionLocal


def run_alembic_upgrade():
    subprocess.check_call(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
    )


def ensure_full_schedule_json():
    schedule_full = BACKEND_DIR / "schedule_full.json"
    if schedule_full.exists():
        return schedule_full
    from scripts.expand_schedule import OUTPUT, generate_schedule

    matches = generate_schedule()
    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print(f"  [OK] 已生成 {OUTPUT.name}（{len(matches)} 场）")
    return schedule_full


def seed_teams_and_schedule(seed_only: bool = False, full_schedule: bool = True):
    settings = get_settings()
    root = settings.repo_root

    if not seed_only:
        run_alembic_upgrade()

    sql_path = root / "data_insert_2026.sql"
    schedule_path = BACKEND_DIR / "schedule.json"

    db = SessionLocal()
    try:
        if sql_path.exists():
            print("→ 导入 48 支球队 ...")
            db.execute(text(sql_path.read_text(encoding="utf-8")))
            db.commit()
            print("  [OK] 球队数据完成")

        print("→ 导入赛程 ...")
        # news_articles / agent_runs 外键引用 matches，需 CASCADE
        db.execute(text("TRUNCATE TABLE matches RESTART IDENTITY CASCADE"))
        if full_schedule:
            src = ensure_full_schedule_json()
        else:
            src = schedule_path
        with src.open(encoding="utf-8") as f:
            schedule = json.load(f)
        for item in schedule:
            db.add(
                Match(
                    group_name=item["group"],
                    match_date=item["date"],
                    match_time=item["time"],
                    team1_name=item["team1"],
                    team2_name=item["team2"],
                    stadium=item["stadium"],
                    round_type=item.get("round_type", "group"),
                    bracket_round=item.get("bracket_round"),
                    bracket_order=item.get("bracket_order"),
                    bracket_meta=item.get("bracket_meta"),
                )
            )
        db.commit()
        print(f"  [OK] 已导入 {len(schedule)} 场比赛（来源 {src.name}）")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Initialize WC2026 database")
    parser.add_argument("--seed-only", action="store_true", help="Only seed data, skip migrations")
    parser.add_argument(
        "--basic-schedule",
        action="store_true",
        help="Use schedule.json (23 matches) instead of full 104",
    )
    args = parser.parse_args()
    seed_teams_and_schedule(seed_only=args.seed_only, full_schedule=not args.basic_schedule)
    if not args.seed_only:
        db = SessionLocal()
        try:
            from app.services.product_catalog_service import ProductCatalogService

            result = ProductCatalogService(db).sync_redeem_catalog()
            print(f"  [OK] 积分兑换商品同步: {result.get('created', 0)} 新建, {result.get('updated', 0)} 更新")
        except Exception as exc:
            print(f"  [WARN] 积分兑换商品同步失败: {exc}")
        finally:
            db.close()
    print("\n[OK] 数据库初始化完成")
    print("可选下一步:")
    print("  python -m scripts.sync_teams --source all")
    print("  python -m scripts.update_starters")
    print("  python -m scripts.build_team_api_mapping")
    print("  （BSD 场次关联会在 ingest 首次同步时自动完成，无需手动 link）")


if __name__ == "__main__":
    main()
