"""Sync redeem products from catalog to database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.services.product_catalog_service import ProductCatalogService


def main():
    parser = argparse.ArgumentParser(description="Sync redeem product catalog to DB")
    parser.add_argument(
        "--deactivate-missing",
        action="store_true",
        help="Deactivate redeem SKUs not in catalog",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        result = ProductCatalogService(db).sync_redeem_catalog(
            deactivate_missing=args.deactivate_missing
        )
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
