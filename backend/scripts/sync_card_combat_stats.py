#!/usr/bin/env python3
"""回填 CollectibleCard.attributes_json 中的 combat_stats。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.combat_stats import build_combat_attrs, merge_combat_into_attributes
from app.db.models import PlayerDetailed
from app.db.models.commerce import CollectibleCard
from app.db.session import SessionLocal


def sync_combat_stats(*, dry_run: bool = False) -> dict[str, int]:
    db = SessionLocal()
    updated = skipped = 0
    try:
        cards = db.query(CollectibleCard).filter(CollectibleCard.active.is_(True)).all()
        player_map = {p.id: p for p in db.query(PlayerDetailed).all()}
        for card in cards:
            attrs = card.attributes_json if isinstance(card.attributes_json, dict) else {}
            if attrs.get("combat_stats") and attrs.get("combat_meta", {}).get("schema_version") == 1:
                skipped += 1
                continue
            player = player_map.get(card.player_id) if card.player_id else None
            combat = build_combat_attrs(
                card_code=card.code,
                series=card.series or "",
                position=attrs.get("position") or (player.position if player else None),
                overall_rating=attrs.get("overall_rating") or (player.overall_rating if player else None),
                player_stats=player.stats if player else None,
            )
            card.attributes_json = merge_combat_into_attributes(attrs, combat)
            updated += 1
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return {"updated": updated, "skipped": skipped, "total": len(cards)}
    finally:
        db.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = sync_combat_stats(dry_run=dry)
    print(result)
