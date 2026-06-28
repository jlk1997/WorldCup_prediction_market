"""Product analytics ingest (frontend funnel + commerce)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth_deps import get_current_user, get_optional_user
from app.api.deps import get_db, require_admin_secret_in_production
from app.db.models.commerce import User
from app.services.product_analytics_service import ProductAnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class AnalyticsEventIn(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=80)
    payload: dict[str, Any] | None = None
    session_id: str | None = Field(default=None, max_length=64)


@router.post("/event")
def track_event(
    body: AnalyticsEventIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    return ProductAnalyticsService(db).track(
        body.event_name,
        user_id=user.id if user else None,
        payload=body.payload,
        session_id=body.session_id,
    )


@router.get("/summary", dependencies=[Depends(require_admin_secret_in_production)])
def analytics_summary(hours: int = 24, db: Session = Depends(get_db)):
    return ProductAnalyticsService(db).summary(hours=min(max(hours, 1), 168))
