#!/usr/bin/env python3
"""生产发布前环境与服务验收脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402


def main() -> int:
    s = get_settings()
    errors: list[str] = []
    warnings: list[str] = []

    if s.production_mode and not (s.redis_url or "").strip():
        errors.append("生产须配置 REDIS_URL（限频/AI 队列/分布式锁）")

    if not s.production_mode:
        warnings.append("PRODUCTION_MODE 未开启")

    if s.alipay_mock:
        errors.append("ALIPAY_MOCK=true，生产须关闭")
    elif not s.alipay_configured:
        errors.append("支付宝证书/APP_ID 未配置完整")

    if s.avata_enabled and s.avata_mock:
        warnings.append("AVATA_ENABLED 但 AVATA_MOCK=true，链上将为 mock")
    elif s.avata_enabled and not s.public_api_base_url:
        errors.append("AVATA 已启用但 PUBLIC_API_BASE_URL 未设置（metadata 须公网可访问）")
    elif s.avata_enabled and s.avata_active and not s.avata_nft_class_id:
        warnings.append("AVATA 已启用但 AVATA_NFT_CLASS_ID 未设置，首次铸造可能自动建类")

    if not s.realname_mock:
        provider = getattr(s, "realname_provider", "api")
        allow_local = getattr(s, "realname_allow_local", False)
        if provider not in ("local", "mock") or (provider == "local" and not allow_local):
            errors.append("REALNAME_MOCK=false 且未配置 local staging 实名渠道")

    if s.jwt_secret in ("", "dev-secret-change-me", "changeme", "change-me-in-production"):
        errors.append("JWT_SECRET 过弱或未设置")

    if not getattr(s, "public_api_base_url", ""):
        warnings.append("PUBLIC_API_BASE_URL 未设置，链 metadata 与回调可能异常")

    print("=== WC2026 生产发布检查 ===")
    print(f"  PRODUCTION_MODE={s.production_mode}")
    print(f"  ALIPAY_MOCK={s.alipay_mock}  configured={s.alipay_configured}")
    print(f"  AVATA_ENABLED={s.avata_enabled}  AVATA_MOCK={s.avata_mock}")
    print(f"  REDIS_URL={'set' if (s.redis_url or '').strip() else 'unset'}")
    print(f"  REALNAME_MOCK={getattr(s, 'realname_mock', True)}")
    if warnings:
        print("\n警告:")
        for w in warnings:
            print(f"  - {w}")
    if errors:
        print("\n错误（须修复后上线）:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n结果: FAIL ({len(errors)} 项)")
        return 1
    print("\n结果: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
