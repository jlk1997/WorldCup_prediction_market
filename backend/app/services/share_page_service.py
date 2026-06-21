"""Build OG metadata for public /share/* HTML pages."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Match, User
from app.db.models.commerce import CollectibleCard, GamePrediction, UserCollectibleCard
from app.services.game_service import GameService
from app.services.referral_service import ReferralService
from app.services.share_token import (
    make_card_share_token,
    make_collectible_share_token,
    mask_nickname,
    parse_card_share_token,
    parse_collectible_share_token,
)


class SharePageService:
    RARITY_ZH = {"common": "普通", "rare": "稀有", "epic": "史诗", "legend": "传奇"}

    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.base = settings.frontend_base_url.rstrip("/")

    def build_card_share_url(self, user: User) -> str:
        token = make_card_share_token(user.id, self.settings.jwt_secret)
        return f"{self.base}/share/card/{token}"

    def build_predict_share_url(self, prediction_id: int) -> str:
        return f"{self.base}/share/predict/{prediction_id}"

    def card_share_page(self, token: str) -> dict | None:
        user_id = parse_card_share_token(token, self.settings.jwt_secret)
        if not user_id:
            return None
        user = self.db.get(User, user_id)
        if not user or user.status != "active":
            return None
        card = GameService(self.db).get_fan_card(user)
        nick = mask_nickname(card.get("nickname"))
        main = (card.get("main_team") or {}).get("name")
        team_hint = f" · 主队 {main}" if main else ""
        title = f"{nick} 的球迷名片 — 最后一舞"
        description = (
            f"累计 {card.get('season_points', 0)} 分 · 胜率 {card.get('win_rate', 0)}%"
            f"{team_hint} · 一起来猜 2026 世界杯"
        )
        ref = card.get("invite_code") or ""
        redirect = f"{self.base}/login?ref={ref}" if ref else f"{self.base}/login"
        return {
            "title": title,
            "description": description,
            "url": f"{self.base}/share/card/{token}",
            "redirect_path": redirect,
        }

    def predict_share_page(self, prediction_id: int) -> dict | None:
        pred = self.db.get(GamePrediction, prediction_id)
        if not pred or pred.status != "won":
            return None
        user = self.db.get(User, pred.user_id)
        match = self.db.get(Match, pred.match_id)
        if not user or not match:
            return None
        nick = mask_nickname(user.nickname)
        t1 = match.team1_name or "?"
        t2 = match.team2_name or "?"
        score = (
            f"{match.home_score}:{match.away_score}"
            if match.home_score is not None and match.away_score is not None
            else None
        )
        pts = pred.points_awarded or 0
        title = f"{nick} 猜中了 {t1} vs {t2} — 最后一舞"
        parts = [f"猜中 +{pts} 累计积分"]
        if score:
            parts.insert(0, f"比分 {score}")
        description = " · ".join(parts) + " · 一起来玩世界杯娱乐竞猜"
        ref = user.invite_code or ""
        redirect = f"{self.base}/login?ref={ref}" if ref else f"{self.base}/predict"
        return {
            "title": title,
            "description": description,
            "url": f"{self.base}/share/predict/{prediction_id}",
            "redirect_path": redirect,
        }

    def rank_share_page(self, period: str = "season") -> dict:
        label = "累计积分榜" if period == "season" else "球迷排行榜"
        title = f"最后一舞 · {label}"
        description = "2026 世界杯娱乐竞猜排行 — 积分、准度、军团榜，一起来冲榜"
        return {
            "title": title,
            "description": description,
            "url": f"{self.base}/share/rank?period={period}",
            "redirect_path": f"{self.base}/leaderboard",
        }

    def build_match_share_url(self, match_id: int, ref: str = "") -> str:
        q = f"?ref={ref}" if ref else ""
        return f"{self.base}/share/match/{match_id}{q}"

    def match_share_page(self, match_id: int, ref: str = "") -> dict | None:
        match = self.db.get(Match, match_id)
        if not match:
            return None
        t1 = match.team1_name or "?"
        t2 = match.team2_name or "?"
        title = f"一起来猜 {t1} vs {t2} — 最后一舞"
        description = f"2026 世界杯娱乐竞猜 · {match.group_name or '世界杯'} · 猜中得积分冲榜"
        code = (ref or "").strip().upper()
        redirect = f"{self.base}/predict?highlight={match_id}"
        if code:
            redirect = f"{self.base}/login?ref={code}&redirect=/predict?highlight={match_id}"
        url = self.build_match_share_url(match_id, code)
        return {
            "title": title,
            "description": description,
            "url": url,
            "redirect_path": redirect,
        }

    def build_collectible_share_url(self, user_id: int, card_code: str) -> str:
        token = make_collectible_share_token(user_id, card_code, self.settings.jwt_secret)
        return f"{self.base}/share/collectible/{token}"

    def build_collectible_share_text(
        self,
        *,
        nickname: str | None,
        card_name: str,
        rarity: str,
        star: int,
        owned: bool,
        share_url: str,
    ) -> str:
        nick = (nickname or "球迷").strip() or "球迷"
        rarity_zh = self.RARITY_ZH.get(rarity, rarity)
        if owned and star > 0:
            line1 = f'我在「最后一舞」收藏了 {card_name} · {rarity_zh}卡 ★{star}'
        elif owned:
            line1 = f'我在「最后一舞」收藏了 {card_name} · {rarity_zh}卡'
        else:
            line1 = f'我在「最后一舞」正在收集 {card_name} · {rarity_zh}卡'
        line2 = "免费 AI 赛事分析 + 猜中掉落数字藏品，一起来玩"
        return f"{line1}\n{line2}\n{share_url}"

    def collectible_share_page(self, token: str) -> dict | None:
        parsed = parse_collectible_share_token(token, self.settings.jwt_secret)
        if not parsed:
            return None
        user_id, card_code = parsed
        user = self.db.get(User, user_id)
        if not user or user.status != "active":
            return None
        card = self.db.query(CollectibleCard).filter(CollectibleCard.code == card_code).first()
        if not card or not card.active:
            return None
        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == user.id, UserCollectibleCard.card_id == card.id)
            .first()
        )
        nick = mask_nickname(user.nickname)
        rarity_zh = self.RARITY_ZH.get(card.rarity or "common", card.rarity or "common")
        owned = row is not None
        if owned:
            star = int(row.star or 1)
            title = f"{nick} 的 {card.name} · {rarity_zh} 藏品"
            description = (
                f"★{star} · 免费 AI 赛事快览 · 猜中掉落数字藏品 · "
                "虚拟收藏无金钱价值，仅供娱乐炫耀"
            )
        else:
            title = f"{nick} 正在收集 {card.name} · {rarity_zh}"
            description = (
                "免费 AI 赛事快览 · 猜中/手册可掉落球星数字藏品 · "
                "虚拟收藏无金钱价值，仅供娱乐炫耀"
            )
        ref = (user.invite_code or "").strip().upper()
        highlight = f"/collection?highlight={card_code}"
        redirect = f"{self.base}{highlight}"
        if ref:
            redirect = f"{self.base}/login?ref={ref}&redirect={highlight}"
        image = card.image_url or ""
        if image.startswith("/"):
            image = f"{self.base}{image}"
        elif not image:
            image = f"{self.base}/share-og.png"
        return {
            "title": title,
            "description": description,
            "url": f"{self.base}/share/collectible/{token}",
            "redirect_path": redirect,
            "image": image,
        }

    def invite_share_page(self, code: str) -> dict:
        redirect_path = f"{self.base}/login?ref={code}" if code else f"{self.base}/login"
        preview = ReferralService(self.db, self.settings).preview_invite_code(code) if code else {"valid": False}
        if preview.get("valid"):
            nick = preview.get("inviter_nickname") or "好友"
            bonus = preview.get("register_invitee_bonus") or 0
            title = f"{nick} 邀请你加入最后一舞"
            description = (
                f"2026 世界杯球迷互动 · 新用户注册得球迷币（含邀请奖励 +{bonus}）"
                " · 免费 AI 赛事快览 · 猜中掉落数字藏品"
            )
            url = f"{self.base}/share/invite?ref={code}"
        else:
            title = "最后一舞：世界杯2026"
            description = "2026 世界杯球迷互动 — 免费 AI 赛事快览 · 竞猜 · 数字藏品 · 擂台与排行榜"
            url = f"{self.base}/share/invite"
        return {
            "title": title,
            "description": description,
            "url": url,
            "redirect_path": redirect_path,
        }
