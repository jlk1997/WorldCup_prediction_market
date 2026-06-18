"""Setup AVATA NFT class for WC2026 collectibles."""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.integrations.avata_client import AvataClient, AvataError


def _ensure_owner(client: AvataClient, settings) -> str:
    owner = (settings.avata_class_owner or "").strip()
    if owner:
        print(f"Using AVATA_CLASS_OWNER={owner}")
        return owner
    op = client.new_operation_id("platform")
    resp = client.create_accounts(count=1, operation_id=op)
    addresses = (resp.get("data") or {}).get("addresses") or []
    owner = addresses[0]["native_address"]
    print("Created platform chain account. Add to backend/.env:")
    print(f"AVATA_CLASS_OWNER={owner}")
    return owner


def main():
    settings = get_settings()
    client = AvataClient()
    if not settings.avata_active:
        print("AVATA not active. Set AVATA_ENABLED=true and configure keys (or AVATA_MOCK=true).")
        return
    if settings.avata_nft_class_id:
        print(f"AVATA_NFT_CLASS_ID already set: {settings.avata_nft_class_id}")
        return

    owner = _ensure_owner(client, settings)
    op = client.new_operation_id("class")
    try:
        client.create_nft_class(settings.avata_nft_class_name, owner=owner, operation_id=op)
    except AvataError as exc:
        print(f"Create class failed: {exc.payload or exc}")
        return

    class_id = None
    for _ in range(15):
        tx = client.query_tx(op)
        data = tx.get("data") or {}
        if data.get("status") == 1:
            class_id = (data.get("nft") or {}).get("class_id")
            break
        if data.get("status") == 2:
            print(f"Create class failed: {data.get('message')}")
            return
        time.sleep(2)

    if not class_id:
        print("Timed out waiting for class_id. Check AVATA console or retry.")
        return
    print("Created NFT class. Add to backend/.env:")
    print(f"AVATA_NFT_CLASS_ID={class_id}")


if __name__ == "__main__":
    main()
