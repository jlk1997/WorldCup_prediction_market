"""Sync collectible card catalog from DB teams/players to database."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.collectible_catalog import build_card_catalog
from app.db.models.commerce import CardSetDefinition, CollectibleCard
from app.db.session import SessionLocal


def main():
    db = SessionLocal()
    try:
        card_defs, set_defs = build_card_catalog(db)
        added_cards = 0
        added_sets = 0
        for cdef in card_defs:
            existing = db.query(CollectibleCard).filter(CollectibleCard.code == cdef["code"]).first()
            if existing:
                if not existing.image_url and cdef.get("image_url"):
                    existing.image_url = cdef["image_url"]
                if cdef.get("is_limited") and not existing.is_limited:
                    existing.is_limited = True
                continue
            db.add(
                CollectibleCard(
                    code=cdef["code"],
                    player_id=cdef.get("player_id"),
                    team_id=cdef.get("team_id"),
                    name=cdef["name"],
                    rarity=cdef["rarity"],
                    series=cdef["series"],
                    image_url=cdef.get("image_url"),
                    attributes_json=cdef.get("attributes_json"),
                    is_limited=cdef.get("is_limited", False),
                    sort_order=cdef.get("sort_order", 0),
                    active=True,
                )
            )
            added_cards += 1
        for sdef in set_defs:
            existing = db.query(CardSetDefinition).filter(CardSetDefinition.code == sdef["code"]).first()
            if existing:
                continue
            db.add(
                CardSetDefinition(
                    code=sdef["code"],
                    name=sdef["name"],
                    description=sdef.get("description"),
                    card_codes=sdef["card_codes"],
                    reward_json=sdef.get("reward_json"),
                    sort_order=sdef.get("sort_order", 0),
                    active=True,
                )
            )
            added_sets += 1
        db.commit()
        from app.services.collectible_service import invalidate_collectible_catalog_cache

        invalidate_collectible_catalog_cache()
        print({"added_cards": added_cards, "added_sets": added_sets, "total_cards": len(card_defs), "total_sets": len(set_defs)})
    finally:
        db.close()


if __name__ == "__main__":
    main()
