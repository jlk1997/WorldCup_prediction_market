"""Generic DB-backed UI configuration."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.commerce import SystemUiConfig


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


class SystemUiConfigService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, config_key: str, default: dict | None = None) -> dict | None:
        row = self.db.query(SystemUiConfig).filter(SystemUiConfig.config_key == config_key).first()
        if not row or not row.config:
            return deepcopy(default) if default is not None else None
        if default is None:
            return deepcopy(row.config)
        return deep_merge(default, row.config)

    def upsert(self, config_key: str, patch: dict, *, default: dict | None = None) -> dict:
        current = self.get(config_key, default=default) or {}
        merged = deep_merge(current, patch)
        row = self.db.query(SystemUiConfig).filter(SystemUiConfig.config_key == config_key).first()
        if row:
            row.config = merged
            row.updated_at = _utcnow()
        else:
            row = SystemUiConfig(config_key=config_key, config=merged)
            self.db.add(row)
        self.db.flush()
        return merged
