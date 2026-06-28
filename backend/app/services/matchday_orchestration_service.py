"""比赛日编排：AI 推送 + 打新活动状态同步 + 复购触达。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Match
from app.db.models.commerce import GamePrediction, MintEvent, MintReservation, User
from app.services.notification_service import NotificationService
from app.services.primary_mint_service import PrimaryMintService

logger = logging.getLogger(__name__)

_REPURCHASE_COPY = {
    "a": (
        "比赛日限定 · {name}",
        "你今日已参与竞猜，限量卡余量不多，首发价抢一张纪念。",
    ),
    "b": (
        "🔥 {name} 开售",
        "忠实球迷专属：今日猜过球的球友可优先入手比赛日卡。",
    ),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MatchdayOrchestrationService:
    def __init__(self, db: Session):
        self.db = db

    def run_matchday_cycle(self) -> dict[str, Any]:
        """Scheduler 入口：临近开赛比赛推送 AI 更新，同步打新状态，复购触达。"""
        today = _utcnow().date()
        tomorrow = today + timedelta(days=1)
        dates = {today.isoformat(), tomorrow.isoformat()}
        matches = (
            self.db.query(Match)
            .filter(
                Match.status.in_(("scheduled", "not_started", "timed", None)),
                Match.match_date.in_(list(dates)),
                Match.team1_name.isnot(None),
                Match.team2_name.isnot(None),
            )
            .order_by(Match.match_date.asc(), Match.match_time.asc())
            .limit(30)
            .all()
        )
        pushes = 0
        for m in matches:
            pushes += self._push_ai_update_for_match(m)
        mint_sync = PrimaryMintService(self.db).sync_event_statuses()
        matchday_live = self._activate_matchday_mints()
        repurchase = self._push_matchday_repurchase(dates)
        if pushes or matchday_live or repurchase:
            self.db.commit()
        return {
            "matches_scanned": len(matches),
            "ai_pushes": pushes,
            "mint_sync": mint_sync,
            "matchday_activated": matchday_live,
            "repurchase_pushes": repurchase,
        }

    def matchday_offer_for_user(self, user: User) -> dict[str, Any] | None:
        """今日主场：用户猜过今日比赛且未购比赛日限量卡时展示入口。"""
        today = _utcnow().date()
        dates = {today.isoformat(), (today + timedelta(days=1)).isoformat()}
        live_mints = (
            self.db.query(MintEvent)
            .filter(
                MintEvent.active.is_(True),
                MintEvent.competition == "matchday_limited",
                MintEvent.status == "live",
            )
            .order_by(MintEvent.id.desc())
            .limit(1)
            .all()
        )
        if not live_mints:
            return None
        ev = live_mints[0]
        if self._user_claimed_matchday(user.id, ev.id):
            return None
        match_ids = [
            row[0]
            for row in self.db.query(Match.id)
            .filter(Match.match_date.in_(list(dates)))
            .limit(50)
            .all()
        ]
        if not match_ids:
            return None
        predicted = (
            self.db.query(GamePrediction.id)
            .filter(GamePrediction.user_id == user.id, GamePrediction.match_id.in_(match_ids))
            .first()
        )
        if not predicted:
            return None
        variant = "a" if user.id % 2 == 0 else "b"
        title, body = _REPURCHASE_COPY[variant]
        return {
            "mint_event_id": ev.id,
            "name": ev.name,
            "remaining": max(0, (ev.total_supply or 0) - (ev.issued or 0)),
            "title": title.format(name=ev.name),
            "body": body,
            "ab_variant": variant,
            "path": f"/mint/{ev.id}",
        }

    def _user_claimed_matchday(self, user_id: int, event_id: int) -> bool:
        row = (
            self.db.query(MintReservation.id)
            .filter(
                MintReservation.user_id == user_id,
                MintReservation.event_id == event_id,
                MintReservation.claimed_count > 0,
            )
            .first()
        )
        return row is not None

    def _push_matchday_repurchase(self, dates: set[str]) -> int:
        live_mints = (
            self.db.query(MintEvent)
            .filter(
                MintEvent.active.is_(True),
                MintEvent.competition == "matchday_limited",
                MintEvent.status == "live",
            )
            .order_by(MintEvent.id.desc())
            .all()
        )
        if not live_mints:
            return 0
        ev = live_mints[0]
        match_ids = [
            row[0]
            for row in self.db.query(Match.id).filter(Match.match_date.in_(list(dates))).limit(80).all()
        ]
        if not match_ids:
            return 0
        predictor_ids = {
            uid
            for (uid,) in self.db.query(GamePrediction.user_id)
            .filter(GamePrediction.match_id.in_(match_ids))
            .distinct()
            .limit(2000)
            .all()
        }
        claimed = {
            uid
            for (uid,) in self.db.query(MintReservation.user_id)
            .filter(
                MintReservation.event_id == ev.id,
                MintReservation.claimed_count > 0,
            )
            .all()
        }
        targets = list(predictor_ids - claimed)[:300]
        ns = NotificationService(self.db)
        count = 0
        for uid in targets:
            variant = "a" if uid % 2 == 0 else "b"
            title_tpl, body = _REPURCHASE_COPY[variant]
            ns._upsert(
                uid,
                "matchday_repurchase",
                title_tpl.format(name=ev.name),
                body,
                ref_type="mint_event",
                ref_id=ev.id,
                payload={
                    "mint_event_id": ev.id,
                    "path": f"/mint/{ev.id}",
                    "ab_variant": variant,
                },
            )
            count += 1
        return count

    def _activate_matchday_mints(self) -> int:
        now = _utcnow()
        rows = (
            self.db.query(MintEvent)
            .filter(
                MintEvent.active.is_(True),
                MintEvent.competition == "matchday_limited",
                MintEvent.status.in_(("scheduled", "reserving")),
                MintEvent.starts_at <= now + timedelta(hours=24),
            )
            .all()
        )
        for ev in rows:
            ev.status = "live"
        return len(rows)

    def _push_ai_update_for_match(self, match: Match) -> int:
        from app.db.models import Team

        t1_name = match.team1_name or ""
        t2_name = match.team2_name or ""
        if not t1_name or not t2_name:
            return 0
        t1 = self.db.query(Team).filter(Team.name == t1_name).first()
        t2 = self.db.query(Team).filter(Team.name == t2_name).first()
        team_ids = [t.id for t in (t1, t2) if t]
        if not team_ids:
            return 0
        label = f"{t1_name} vs {t2_name}"
        users = (
            self.db.query(User.id)
            .filter(User.favorite_team_id.in_(team_ids), User.status == "active")
            .limit(500)
            .all()
        )
        ns = NotificationService(self.db)
        count = 0
        for (uid,) in users:
            ns._upsert(
                uid,
                "matchday_ai",
                f"AI 已更新 · {label}",
                "主队即将开赛，查看 AI 倾向与竞猜参考。",
                ref_type="match",
                ref_id=match.id,
                payload={"match_id": match.id, "path": f"/predict?highlight={match.id}"},
            )
            count += 1
        return count
