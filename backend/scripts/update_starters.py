"""Update starter flags for all teams."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.services.starter_selector import update_all_starters


def main():
    db = SessionLocal()
    try:
        count = update_all_starters(db)
        print(f"Starters updated for {count} teams")
    finally:
        db.close()


if __name__ == "__main__":
    main()
