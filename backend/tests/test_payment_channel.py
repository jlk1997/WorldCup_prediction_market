"""Alipay page vs WAP pay channel tests."""

from pathlib import Path

import pytest

from app.services.payment_service import PaymentService
from app.utils.pay_channel import is_mobile_user_agent, resolve_pay_channel


def test_resolve_pay_channel_explicit():
    assert resolve_pay_channel("page", "Mozilla/5.0 (iPhone)") == "page"
    assert resolve_pay_channel("wap", "Mozilla/5.0 (Windows NT)") == "wap"


def test_resolve_pay_channel_auto_mobile():
    ua = "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36"
    assert resolve_pay_channel("auto", ua) == "wap"
    assert is_mobile_user_agent(ua) is True


def test_resolve_pay_channel_auto_desktop():
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    assert resolve_pay_channel("auto", ua) == "page"
    assert is_mobile_user_agent(ua) is False


def test_resolve_pay_channel_ipad_uses_page():
    ua = "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)"
    assert resolve_pay_channel("auto", ua) == "page"
    assert is_mobile_user_agent(ua) is False


@pytest.fixture
def cert_dir(tmp_path: Path):
    priv = tmp_path / "app_private.pem"
    app_crt = tmp_path / "app.crt"
    ali_crt = tmp_path / "alipay.crt"
    root_crt = tmp_path / "root.crt"
    for f in (priv, app_crt, ali_crt, root_crt):
        f.write_text("placeholder", encoding="utf-8")
    return priv, app_crt, ali_crt, root_crt


def test_build_pay_url_uses_wap_on_mobile_channel(cert_dir, monkeypatch):
    from app.core.config import Settings

    priv, app_crt, ali_crt, root_crt = cert_dir
    settings = Settings(
        alipay_app_id="2021000123456789",
        alipay_private_key_path=str(priv),
        alipay_app_cert_path=str(app_crt),
        alipay_alipay_cert_path=str(ali_crt),
        alipay_root_cert_path=str(root_crt),
        alipay_notify_url="https://example.com/notify",
        alipay_return_url="https://example.com/return",
        alipay_mock=False,
        alipay_sandbox=False,
    )

    calls: list[str] = []

    class FakeDCAliPay:
        def __init__(self, **kwargs):
            pass

        def api_alipay_trade_page_pay(self, **kwargs):
            calls.append("page")
            return "page=1"

        def api_alipay_trade_wap_pay(self, **kwargs):
            calls.append("wap")
            return "wap=1"

    monkeypatch.setattr("alipay.DCAliPay", FakeDCAliPay)

    svc = PaymentService(db=None, settings=settings)  # type: ignore[arg-type]

    class FakeOrder:
        out_trade_no = "WC20260101120000TEST"
        amount_fen = 600

    class FakeProduct:
        name = "球迷币 - 小包"

    url_page = svc._build_pay_url(FakeOrder(), FakeProduct(), "page")
    url_wap = svc._build_pay_url(FakeOrder(), FakeProduct(), "wap")

    assert calls == ["page", "wap"]
    assert "page=1" in url_page
    assert "wap=1" in url_wap
    assert url_page.startswith("https://openapi.alipay.com/gateway.do?")
    assert url_wap.startswith("https://openapi.alipay.com/gateway.do?")
