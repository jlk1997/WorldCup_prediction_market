"""Alipay certificate-mode configuration tests."""

from pathlib import Path

import pytest

from app.core.config import Settings, get_settings


@pytest.fixture
def cert_dir(tmp_path: Path):
    priv = tmp_path / "app_private.pem"
    app_crt = tmp_path / "app.crt"
    ali_crt = tmp_path / "alipay.crt"
    root_crt = tmp_path / "root.crt"
    for f in (priv, app_crt, ali_crt, root_crt):
        f.write_text("placeholder", encoding="utf-8")
    return tmp_path, priv, app_crt, ali_crt, root_crt


def test_alipay_configured_false_when_missing_cert(cert_dir):
    tmp_path, priv, app_crt, ali_crt, root_crt = cert_dir
    ali_crt.unlink()
    s = Settings(
        alipay_app_id="2021000123456789",
        alipay_private_key_path=str(priv),
        alipay_app_cert_path=str(app_crt),
        alipay_alipay_cert_path=str(ali_crt),
        alipay_root_cert_path=str(root_crt),
    )
    assert s.alipay_configured is False


def test_alipay_configured_true_when_all_files_present(cert_dir):
    tmp_path, priv, app_crt, ali_crt, root_crt = cert_dir
    s = Settings(
        alipay_app_id="2021000123456789",
        alipay_private_key_path=str(priv),
        alipay_app_cert_path=str(app_crt),
        alipay_alipay_cert_path=str(ali_crt),
        alipay_root_cert_path=str(root_crt),
    )
    assert s.alipay_configured is True


def test_alipay_configured_false_for_placeholder_app_id(cert_dir):
    tmp_path, priv, app_crt, ali_crt, root_crt = cert_dir
    s = Settings(
        alipay_app_id="请填写_支付宝AppID",
        alipay_private_key_path=str(priv),
        alipay_app_cert_path=str(app_crt),
        alipay_alipay_cert_path=str(ali_crt),
        alipay_root_cert_path=str(root_crt),
    )
    assert s.alipay_configured is False


def test_build_alipay_client_uses_dc_alipay(cert_dir, monkeypatch):
    from app.services.payment_service import PaymentService

    tmp_path, priv, app_crt, ali_crt, root_crt = cert_dir
    settings = Settings(
        alipay_app_id="2021000123456789",
        alipay_private_key_path=str(priv),
        alipay_app_cert_path=str(app_crt),
        alipay_alipay_cert_path=str(ali_crt),
        alipay_root_cert_path=str(root_crt),
        alipay_notify_url="http://example.com/notify",
    )
    captured = {}

    class FakeDCAliPay:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("alipay.DCAliPay", FakeDCAliPay)

    svc = PaymentService(db=None, settings=settings)  # type: ignore[arg-type]
    svc._build_alipay_client()

    assert captured["appid"] == "2021000123456789"
    assert "app_public_key_cert_string" in captured
    assert "alipay_public_key_cert_string" in captured
    assert "alipay_root_cert_string" in captured
    assert "alipay_public_key_string" not in captured


def test_production_requires_alipay_certs(monkeypatch):
    monkeypatch.setenv("PRODUCTION_MODE", "true")
    monkeypatch.setenv("ALIPAY_MOCK", "false")
    monkeypatch.setenv("ALIPAY_SANDBOX", "false")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    monkeypatch.setenv("DB_PASSWORD", "not-postgres-default")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
    monkeypatch.setenv("AUTH_DEV_MODE", "false")
    get_settings.cache_clear()

    from app.main import _validate_production_settings

    with pytest.raises(RuntimeError, match="支付宝证书"):
        _validate_production_settings(get_settings())
    get_settings.cache_clear()
