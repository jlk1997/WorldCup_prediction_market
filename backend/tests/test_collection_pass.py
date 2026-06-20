"""Collection Pass service tests."""

import uuid

import pytest
from datetime import timedelta
from sqlalchemy.orm import Session

from app.data.collection_pass_catalog import MAX_LEVEL, XP_SOURCES
from app.db.models.commerce import (
    CollectionPassProgress,
    CollectionPassSeason,
    CollectionPassXpLog,
    User,
)
from app.db.session import SessionLocal
from app.services.collection_pass_service import CollectionPassService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _user(db: Session) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"pass_{suffix}@test.com", nickname="passer", fan_coins=500)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _season(db: Session) -> CollectionPassSeason:
    season = (
        db.query(CollectionPassSeason)
        .filter(CollectionPassSeason.code == "wc2026_s1")
        .first()
    )
    if season:
        return season
    from app.data.collection_pass_catalog import get_season_config, season_window

    start, end = season_window()
    season = CollectionPassSeason(
        code="wc2026_s1",
        name="test season",
        starts_at=start,
        ends_at=end,
        max_level=MAX_LEVEL,
        config_json=get_season_config(),
        active=True,
    )
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


def test_award_xp_idempotent(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    r1 = svc.award_xp(user, "predict_submit", "game_prediction", 9001, XP_SOURCES["predict_submit"])
    db.commit()
    assert r1["awarded"] == XP_SOURCES["predict_submit"]
    r2 = svc.award_xp(user, "predict_submit", "game_prediction", 9001, XP_SOURCES["predict_submit"])
    assert r2["awarded"] == 0
    assert r2["reason"] == "duplicate"


def test_claim_level_free(db: Session):
    user = _user(db)
    season = _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, season)
    progress.xp = 99999
    progress.level = MAX_LEVEL
    db.commit()
    result = svc.claim_level_reward(user, 1, "free")
    db.commit()
    assert result["level"] == 1
    assert "grants" in result
    progress = db.query(CollectionPassProgress).filter(CollectionPassProgress.user_id == user.id).first()
    assert 1 in (progress.claimed_free_json or [])


def test_unlock_premium(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    res = svc.unlock_premium(user)
    db.commit()
    assert res.get("premium_unlocked") is True
    summary = svc.get_summary(user)
    assert summary["premium_unlocked"] is True


def test_buy_xp_boost(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    before = user.fan_coins
    res = svc.buy_xp_boost(user)
    db.commit()
    assert res["cost"] > 0
    db.refresh(user)
    assert user.fan_coins < before


def test_claim_level_duplicate(db: Session):
    from app.core.exceptions import BadRequestError

    user = _user(db)
    season = _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, season)
    progress.xp = 99999
    progress.level = MAX_LEVEL
    progress.claimed_free_json = [1]
    db.commit()
    with pytest.raises(BadRequestError, match="已领取"):
        svc.claim_level_reward(user, 1, "free")


def test_premium_backfill_on_unlock(db: Session):
    from app.data.collection_pass_catalog import LEVEL_THRESHOLDS

    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, svc._get_active_season())
    progress.xp = LEVEL_THRESHOLDS[4]
    progress.level = 4
    db.commit()
    res = svc.unlock_premium(user)
    db.commit()
    assert res.get("premium_unlocked") is True
    assert res.get("backfill_count") == 4
    db.refresh(progress)
    assert progress.premium_unlocked is True
    assert len(progress.claimed_premium_json or []) == 4


def test_grant_level_skip(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    res = svc.grant_level_skip(user, 10)
    db.commit()
    assert res["skipped_levels"] == 10
    assert res["level"] == 10


def test_bump_quest_awards_xp(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    before = (
        db.query(CollectionPassXpLog)
        .filter(CollectionPassXpLog.user_id == user.id)
        .count()
    )
    for _ in range(3):
        svc.bump_quest(user, "predict_win")
    db.commit()
    after = (
        db.query(CollectionPassXpLog)
        .filter(CollectionPassXpLog.user_id == user.id)
        .count()
    )
    assert after > before


def test_event_limited_available_on_matchday(db: Session):
    from app.db.models.commerce import CollectibleCard, CollectibleEvent
    from app.services.collectible_service import CollectibleService

    user = _user(db)
    _season(db)
    card = CollectibleCard(
        code=f"evt_{uuid.uuid4().hex[:6]}",
        name="Event Test",
        rarity="epic",
        series="event_limited",
        active=True,
    )
    db.add(card)
    event = CollectibleEvent(
        code=f"test_evt_{uuid.uuid4().hex[:6]}",
        name="Test Event",
        description="test",
        starts_at=_utcnow() - timedelta(days=1),
        ends_at=_utcnow() + timedelta(days=1),
        event_series="event_limited",
        boost_json={"matchday_series_weight": 2.0},
        coin_action_cost=15,
        active=True,
    )
    db.add(event)
    db.commit()
    svc = CollectibleService(db)
    assert svc._is_card_available(card, "matchday") is True
    assert svc._is_card_available(card, "predict_win") is False


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_plus_bundle_skip_then_backfill(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    skip = svc.grant_level_skip(user, 10)
    unlock = svc.unlock_premium(user)
    db.commit()
    assert skip["level"] == 10
    assert unlock["premium_unlocked"] is True
    assert unlock["backfill_count"] == 10


def test_summary_claimable_count(db: Session):
    from app.data.collection_pass_catalog import LEVEL_THRESHOLDS

    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, svc._get_active_season())
    progress.xp = LEVEL_THRESHOLDS[3]
    progress.level = 3
    progress.premium_unlocked = True
    db.commit()
    summary = svc.get_summary(user)
    assert summary["claimable_count"] == 6  # 3 free + 3 premium


def test_summary_lite_has_no_tracks(db: Session):
    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    lite = svc.get_summary_lite(user)
    assert "tracks" not in lite
    assert "claimed_free_levels" in lite
    assert lite["quests"]["daily"]


def test_track_catalog_cached(db: Session):
    _season(db)
    svc = CollectionPassService(db)
    cat1 = svc.get_track_catalog()
    cat2 = svc.get_track_catalog()
    assert cat1["max_level"] == MAX_LEVEL
    assert len(cat1["tracks"]) == MAX_LEVEL
    assert cat1 is cat2 or cat1 == cat2


def test_merge_tracks_with_progress(db: Session):
    from app.data.collection_pass_catalog import LEVEL_THRESHOLDS

    user = _user(db)
    season = _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, season)
    progress.xp = LEVEL_THRESHOLDS[2]
    progress.level = 2
    progress.premium_unlocked = True
    db.commit()
    catalog = svc.get_track_catalog(season)
    merged = svc.merge_tracks_with_progress(catalog, progress)
    assert merged[1]["free_claimable"] is True
    assert merged[1]["premium_claimable"] is True
    assert merged[0]["free_claimed"] is False


def test_pass_nudge_matches_summary(db: Session):
    from app.data.collection_pass_catalog import LEVEL_THRESHOLDS

    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, svc._get_active_season())
    progress.xp = LEVEL_THRESHOLDS[2]
    progress.level = 2
    progress.premium_unlocked = True
    db.commit()
    summary = svc.get_summary(user)
    nudge = svc.pass_nudge(user)
    assert nudge is not None
    assert nudge["claimable_count"] == summary["claimable_count"]
    assert nudge["level"] == summary["level"]


def test_claim_all_rewards(db: Session):
    from app.data.collection_pass_catalog import LEVEL_THRESHOLDS

    user = _user(db)
    _season(db)
    svc = CollectionPassService(db)
    progress = svc._get_or_create_progress(user, svc._get_active_season())
    progress.xp = LEVEL_THRESHOLDS[3]
    progress.level = 3
    progress.premium_unlocked = True
    db.commit()
    result = svc.claim_all_rewards(user)
    db.commit()
    assert result["claimed_count"] == 6
    assert len(result["claims"]) == 6
    summary = svc.get_summary(user)
    assert summary["claimable_count"] == 0


def test_event_cheer_requires_main_team(db: Session):
    from app.core.exceptions import BadRequestError
    from app.services.collectible_service import CollectibleService

    user = _user(db)
    _season(db)
    svc = CollectibleService(db)
    with pytest.raises(BadRequestError, match="主队"):
        svc.event_cheer_drop(user, 1)


def test_coin_shard_fill_cap(db: Session):
    from app.core.exceptions import BadRequestError
    from app.services.collectible_service import CollectibleService

    user = _user(db)
    _season(db)
    svc = CollectibleService(db)
    with pytest.raises(BadRequestError):
        svc._buy_shards_with_coins(user, "common", 9999)
