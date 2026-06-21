"""Tests for share token signing."""

from app.services.share_token import (
    make_card_share_token,
    make_collectible_share_token,
    mask_nickname,
    parse_card_share_token,
    parse_collectible_share_token,
)


def test_card_share_token_roundtrip():
    secret = "test-secret"
    token = make_card_share_token(42, secret)
    assert parse_card_share_token(token, secret) == 42
    assert parse_card_share_token(token, "wrong") is None
    assert parse_card_share_token("bad", secret) is None


def test_mask_nickname():
    assert mask_nickname("张三") == "张**"
    assert mask_nickname("A") == "A*"


def test_collectible_share_token_roundtrip():
    secret = "test-secret"
    token = make_collectible_share_token(7, "legend_ronaldo", secret)
    parsed = parse_collectible_share_token(token, secret)
    assert parsed == (7, "legend_ronaldo")
    assert parse_collectible_share_token(token, "wrong") is None
