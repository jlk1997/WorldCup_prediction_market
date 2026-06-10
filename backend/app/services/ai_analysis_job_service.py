"""Persisted AI analysis jobs for crash recovery and refund."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.commerce import AiAnalysisJob
from app.services.ai_billing_service import AiBillingService, BillingDecision

logger = logging.getLogger(__name__)

STALE_JOB_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AiAnalysisJobService:
    def __init__(self, db: Session):
        self.db = db

    def start_job(
        self,
        *,
        user_id: int,
        team1: str,
        team2: str,
        mode: str,
        force_refresh: bool,
        billing: BillingDecision,
    ) -> int:
        row = AiAnalysisJob(
            user_id=user_id,
            team1=team1,
            team2=team2,
            mode=mode,
            force_refresh=force_refresh,
            status="running",
            billing_json=billing.to_dict(),
            started_at=_utcnow(),
        )
        self.db.add(row)
        self.db.flush()
        return row.id

    def complete_job(self, job_id: int, agent_run_id: int) -> None:
        row = self.db.get(AiAnalysisJob, job_id)
        if not row:
            return
        row.status = "completed"
        row.agent_run_id = agent_run_id
        row.finished_at = _utcnow()

    def fail_job(self, job_id: int, message: str, *, refunded: bool) -> None:
        row = self.db.get(AiAnalysisJob, job_id)
        if not row or row.status != "running":
            return
        row.status = "refunded" if refunded else "failed"
        row.error_message = (message or "")[:2000]
        row.finished_at = _utcnow()

    def recover_stale_jobs(self, stale_minutes: int = STALE_JOB_MINUTES) -> int:
        cutoff = _utcnow() - timedelta(minutes=stale_minutes)
        rows = (
            self.db.query(AiAnalysisJob)
            .filter(AiAnalysisJob.status == "running", AiAnalysisJob.started_at < cutoff)
            .all()
        )
        recovered = 0
        billing = AiBillingService(self.db)
        for row in rows:
            try:
                payload = row.billing_json or {}
                decision = BillingDecision(
                    charge_coins=int(payload.get("charge_coins") or 0),
                    used_free_quota=bool(payload.get("used_free_quota")),
                    free_remaining=int(payload.get("free_remaining") or 0),
                    daily_free_limit=int(payload.get("daily_free_limit") or 0),
                    mode=str(payload.get("mode") or row.mode),
                    force_refresh=bool(payload.get("force_refresh")),
                )
                billing.refund_charge(row.user_id, decision)
                row.status = "refunded"
                row.error_message = "服务中断，已自动退还本次扣费"
                row.finished_at = _utcnow()
                recovered += 1
            except Exception:
                logger.exception("Stale AI job recovery failed for job_id=%s", row.id)
                self.db.rollback()
                continue
        if recovered:
            self.db.commit()
            logger.info("Recovered %s stale AI analysis jobs", recovered)
        return recovered
