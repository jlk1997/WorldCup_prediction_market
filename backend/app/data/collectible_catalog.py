"""Collectible card catalog — bootstrap from DB teams/players + static legends."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.data.combat_stats import build_combat_attrs, merge_combat_into_attributes
from app.db.models import PlayerDetailed, Team

RARITIES = ("common", "rare", "epic", "legend")

LEGEND_CARD_DEFS: list[dict] = [
    {
        "code": "legend_messi",
        "name": "梅西 · 最后一舞",
        "rarity": "legend",
        "series": "legend",
        "image_url": "/legends/messi.webp",
        "attributes_json": {"tagline": "最后一舞 · 魔术师", "accent": "#7eb8ff"},
        "sort_order": 1,
    },
    {
        "code": "legend_ronaldo",
        "name": "C罗 · 最后一舞",
        "rarity": "legend",
        "series": "legend",
        "image_url": "/legends/ronaldo.webp",
        "attributes_json": {"tagline": "最后一舞 · 王者气场", "accent": "#e8c88a"},
        "sort_order": 2,
    },
    {
        "code": "legend_neymar",
        "name": "内马尔 · 最后一舞",
        "rarity": "legend",
        "series": "legend",
        "image_url": "/legends/neymar.webp",
        "attributes_json": {"tagline": "最后一舞 · 桑巴 flair", "accent": "#c9788a"},
        "sort_order": 3,
    },
]

SHARD_ON_DUPLICATE: dict[str, int] = {
    "common": 5,
    "rare": 15,
    "epic": 40,
    "legend": 100,
}

SYNTHESIS_COST: dict[str, dict[str, int]] = {
    "common": {"shards": 50, "redeem_points": 30},
    "rare": {"shards": 150, "redeem_points": 80},
    "epic": {"shards": 400, "redeem_points": 200},
}

UPGRADE_STAR_COST: dict[int, dict[str, int]] = {
    2: {"shards": 20, "redeem_points": 50},
    3: {"shards": 50, "redeem_points": 100},
}

DROP_WEIGHTS_BY_SOURCE: dict[str, dict[str, float]] = {
    "predict_win": {"common": 0.55, "rare": 0.28, "epic": 0.14, "legend": 0.03},
    "signin": {"common": 0.35, "rare": 0.45, "epic": 0.18, "legend": 0.02},
    "matchday": {"common": 0.25, "rare": 0.45, "epic": 0.25, "legend": 0.05},
    "referral": {"common": 0.20, "rare": 0.40, "epic": 0.30, "legend": 0.10},
    "synthesis": {"common": 1.0, "rare": 0.0, "epic": 0.0, "legend": 0.0},
    "event_cheer": {"common": 0.20, "rare": 0.35, "epic": 0.35, "legend": 0.10},
    "duel_win": {"common": 0.45, "rare": 0.35, "epic": 0.17, "legend": 0.03},
    "duel_daily_win": {"common": 0.30, "rare": 0.40, "epic": 0.25, "legend": 0.05},
    "duel_streak": {"common": 0.20, "rare": 0.35, "epic": 0.35, "legend": 0.10},
    "duel_season_reward": {"common": 0.15, "rare": 0.35, "epic": 0.35, "legend": 0.15},
    "duel_chain_bonus": {"common": 0.10, "rare": 0.30, "epic": 0.40, "legend": 0.20},
    "duel_loss_comfort": {"common": 0.60, "rare": 0.30, "epic": 0.10, "legend": 0.00},
    "collection_pass": {"common": 0.0, "rare": 0.0, "epic": 0.5, "legend": 0.5},
}


def rating_to_rarity(rating: int | None, is_starter: bool = False) -> str:
    if rating is None:
        return "common"
    if rating >= 88:
        return "legend"
    if rating >= 84:
        return "epic"
    if rating >= 78 or is_starter:
        return "rare"
    return "common"


def build_card_catalog(db: Session) -> tuple[list[dict], list[dict]]:
    """Return (card_defs, set_defs) from current DB state."""
    cards: list[dict] = []
    sort = 100

    for legend in LEGEND_CARD_DEFS:
        cards.append({**legend, "player_id": None, "team_id": None, "is_limited": False})

    teams = db.query(Team).order_by(Team.group_name, Team.name).all()
    team_code_map: dict[int, str] = {}
    team_logos: dict[int, str | None] = {t.id: t.logo_url for t in teams}

    for team in teams:
        sort += 1
        crest_code = f"team_crest_{team.id}"
        team_code_map[team.id] = crest_code
        cards.append(
            {
                "code": crest_code,
                "player_id": None,
                "team_id": team.id,
                "name": f"{team.name} · 队徽典藏",
                "rarity": "rare",
                "series": "team_crest",
                "image_url": team.logo_url,
                "attributes_json": {
                    "group_name": team.group_name,
                    "country_code": team.country_code,
                },
                "is_limited": False,
                "sort_order": sort,
            }
        )
        sort += 1
        cards.append(
            {
                "code": f"matchday_{team.id}",
                "player_id": None,
                "team_id": team.id,
                "name": f"{team.name} · 比赛日限定",
                "rarity": "epic",
                "series": "matchday_limited",
                "image_url": team.logo_url,
                "attributes_json": {
                    "group_name": team.group_name,
                    "tagline": "比赛日动员专属",
                    "limited": True,
                },
                "is_limited": True,
                "sort_order": sort,
            }
        )

    players = (
        db.query(PlayerDetailed)
        .filter(PlayerDetailed.overall_rating.isnot(None))
        .order_by(PlayerDetailed.team_id, PlayerDetailed.overall_rating.desc())
        .all()
    )
    starter_codes: dict[int, list[str]] = {}

    for player in players:
        sort += 1
        rarity = rating_to_rarity(player.overall_rating, bool(player.is_starter))
        code = f"player_{player.id}"
        cards.append(
            {
                "code": code,
                "player_id": player.id,
                "team_id": player.team_id,
                "name": player.name,
                "rarity": rarity,
                "series": "team_squad",
                "image_url": team_logos.get(player.team_id),
                "attributes_json": merge_combat_into_attributes(
                    {
                        "position": player.position,
                        "overall_rating": player.overall_rating,
                        "is_starter": bool(player.is_starter),
                        "club": player.club,
                    },
                    build_combat_attrs(
                        card_code=code,
                        series="team_squad",
                        position=player.position,
                        overall_rating=player.overall_rating,
                        player_stats=player.stats if isinstance(player.stats, dict) else None,
                    ),
                ),
                "is_limited": False,
                "sort_order": sort,
            }
        )
        if player.is_starter:
            starter_codes.setdefault(player.team_id, []).append(code)

    set_defs: list[dict] = [
        {
            "code": "legend_last_dance",
            "name": "传奇 · 最后一舞",
            "description": "集齐梅西、C罗、内马尔传奇卡",
            "card_codes": [c["code"] for c in LEGEND_CARD_DEFS],
            "reward_json": {
                "badge_code": "collectible_legend_set",
                "badge_title": "传奇收藏家",
                "fan_coins": 200,
                "redeem_points": 80,
            },
            "sort_order": 1,
        }
    ]

    group_cards: dict[str, list[str]] = {}
    for card in cards:
        if card["series"] == "team_crest":
            group = (card.get("attributes_json") or {}).get("group_name")
            if group:
                group_cards.setdefault(str(group), []).append(card["code"])

    sort_set = 10
    for group_name, crest_codes in sorted(group_cards.items()):
        if len(crest_codes) < 2:
            continue
        sort_set += 1
        set_defs.append(
            {
                "code": f"group_{group_name.lower()}",
                "name": f"小组 {group_name} · 队徽套",
                "description": f"集齐小组 {group_name} 全部队徽典藏卡",
                "card_codes": crest_codes,
                "reward_json": {
                    "badge_code": f"collectible_group_{group_name.lower()}",
                    "badge_title": f"{group_name}组收藏家",
                    "fan_coins": 150,
                    "redeem_points": 60,
                },
                "sort_order": sort_set,
            }
        )

    for team_id, codes in starter_codes.items():
        if len(codes) < 5:
            continue
        team = db.get(Team, team_id)
        if not team:
            continue
        sort_set += 1
        set_defs.append(
            {
                "code": f"team_starters_{team_id}",
                "name": f"{team.name} · 首发阵容",
                "description": f"集齐 {team.name} 首发球星卡（至少 {min(len(codes), 11)} 张）",
                "card_codes": codes[:11],
                "reward_json": {
                    "badge_code": f"collectible_team_{team_id}",
                    "badge_title": f"{team.name}阵容收藏家",
                    "fan_coins": 100,
                    "redeem_points": 50,
                },
                "sort_order": sort_set,
            }
        )

    return cards, set_defs


def pass_and_event_cards() -> tuple[list[dict], list[dict]]:
    from app.data.collection_pass_catalog import EVENT_SET_DEFS, PASS_LIMITED_CARD_DEFS

    return list(PASS_LIMITED_CARD_DEFS), list(EVENT_SET_DEFS)
