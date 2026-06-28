"""Dashboard「今日主场」聚合：竞猜待办 + 资产 hub + 打新/链状态。"""



from __future__ import annotations



from typing import Any



from sqlalchemy.orm import Session



from app.core.cache import cache_get, cache_set

from app.core.user_surface_cache import (

    LIVE_MINTS_TTL,

    TODAY_HOME_TTL,

    invalidate_user_surface,

    today_home_key,

)

from app.db.models.commerce import MintEvent, User

from app.services.asset_hub_service import AssetHubService

from app.services.game_service import GameService

from app.services.matchday_orchestration_service import MatchdayOrchestrationService



LIVE_MINTS_CACHE_KEY = "mint:live_cards_v1"





class TodayHomeService:

    def __init__(self, db: Session):

        self.db = db



    def build(self, user: User, *, use_cache: bool = True) -> dict[str, Any]:

        cache_key = today_home_key(user.id)

        if use_cache:

            cached = cache_get(cache_key)

            if cached:

                return cached



        daily = GameService(self.db).get_daily_status(user)

        hub = AssetHubService(self.db).hub_summary(user, light=True)

        mint_cards = self._live_mint_cards()

        from app.services.collectible_service import CollectibleService



        chain_summary = CollectibleService(self.db).get_chain_status(user)

        pending_chain = int(chain_summary.get("pending_mints") or 0)

        todos: list[dict[str, Any]] = []

        if daily.get("next_predictable_match"):

            todos.append(

                {

                    "kind": "predict",

                    "label": "下一场可竞猜",

                    "detail": daily["next_predictable_match"].get("label"),

                    "path": f"/predict?highlight={daily['next_predictable_match'].get('match_id')}",

                }

            )

        if hub.get("claimable_stake_points", 0) > 0:

            todos.append(

                {

                    "kind": "stake",

                    "label": "质押可领取",

                    "detail": f"{hub['claimable_stake_points']} 积分待领",

                    "path": "/collection?tab=stake",

                }

            )

        if hub.get("duel_pending_incoming", 0) > 0:

            todos.append(

                {

                    "kind": "duel",

                    "label": "对决待应战",

                    "detail": f"{hub['duel_pending_incoming']} 场挑战",

                    "path": "/arena#duel",

                }

            )

        if mint_cards:

            todos.append(

                {

                    "kind": "mint",

                    "label": "限量打新进行中",

                    "detail": mint_cards[0]["name"],

                    "path": f"/mint/{mint_cards[0]['id']}",

                }

            )

        if pending_chain > 0:

            todos.append(

                {

                    "kind": "chain",

                    "label": "链上铸造中",

                    "detail": f"{pending_chain} 张卡处理中",

                    "path": "/collection",

                }

            )

        matchday_offer = MatchdayOrchestrationService(self.db).matchday_offer_for_user(user)

        if matchday_offer:

            todos.insert(

                0,

                {

                    "kind": "mint",

                    "label": matchday_offer.get("title") or "比赛日限定",

                    "detail": matchday_offer.get("body") or matchday_offer.get("name", ""),

                    "path": matchday_offer.get("path") or f"/mint/{matchday_offer['mint_event_id']}",

                },

            )

        ritual = daily.get("ritual_progress") or {}

        payload = {

            "daily": daily,

            "hub": hub,

            "live_mints": mint_cards,

            "pending_chain_mints": pending_chain,

            "failed_chain_mints": chain_summary.get("failed_mints") or 0,

            "first_failed_user_card_id": chain_summary.get("first_failed_user_card_id"),

            "chain_enabled": chain_summary.get("enabled"),

            "todos": todos[:6],

            "ritual_done": ritual.get("done", 0),

            "ritual_total": ritual.get("total", 3),

            "match_day": bool(daily.get("match_day")),

            "matchday_offer": matchday_offer,

        }

        if use_cache:

            cache_set(cache_key, payload, ttl=TODAY_HOME_TTL)

        return payload



    def _live_mint_cards(self) -> list[dict[str, Any]]:

        cached = cache_get(LIVE_MINTS_CACHE_KEY)

        if cached is not None:

            return cached

        live_mints = (

            self.db.query(MintEvent)

            .filter(MintEvent.active.is_(True), MintEvent.status == "live")

            .order_by(MintEvent.id.desc())

            .limit(3)

            .all()

        )

        mint_cards = [

            {

                "id": ev.id,

                "name": ev.name,

                "remaining": max(0, (ev.total_supply or 0) - (ev.issued or 0)),

                "currency": ev.currency,

                "price_fen": ev.price_fen,

                "price_coins": ev.price_coins,

            }

            for ev in live_mints

        ]

        cache_set(LIVE_MINTS_CACHE_KEY, mint_cards, ttl=LIVE_MINTS_TTL)

        return mint_cards





def bust_today_home_cache(user_id: int) -> None:

    invalidate_user_surface(user_id)


