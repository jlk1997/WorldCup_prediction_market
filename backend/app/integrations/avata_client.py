"""AVATA Open API client for 文昌链 native NFT (v3).

Docs: https://docs.avata.bianjie.ai/
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AvataError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class AvataClient:
    """Signed HTTP client for AVATA v3 native module."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.avata_enabled and self.settings.avata_configured

    @property
    def mock_mode(self) -> bool:
        return self.settings.avata_mock or not self.settings.avata_configured

    def new_operation_id(self, prefix: str = "wc2026") -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    def _sign(self, path: str, params: dict[str, Any], data: dict[str, Any], timestamp: str) -> str:
        merged: dict[str, Any] = {"path_url": path}
        for key, value in params.items():
            merged[f"query_{key}"] = value
        for key, value in data.items():
            merged[f"body_{key}"] = value
        sorted_str = json.dumps(dict(sorted(merged.items())), separators=(",", ":"), ensure_ascii=False)
        sign_str = sorted_str + timestamp + self.settings.avata_api_secret
        return hashlib.sha256(sign_str.encode("utf-8")).hexdigest()

    def _headers(self, path: str, params: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
        timestamp = str(int(__import__("time").time() * 1000))
        signature = self._sign(path, params, data, timestamp)
        return {
            "Content-Type": "application/json",
            "X-Api-Key": self.settings.avata_api_key,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: float = 20.0,
    ) -> dict[str, Any]:
        if self.mock_mode:
            return self._mock_response(method, path, data or {})

        params = params or {}
        data = data or {}
        url = self.settings.avata_host.rstrip("/") + path
        headers = self._headers(path, params, data)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, params=params, json=data if data else None, headers=headers)
        except httpx.HTTPError as exc:
            raise AvataError(f"AVATA HTTP error: {exc}") from exc

        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text}

        if resp.status_code >= 400:
            raise AvataError(
                f"AVATA API error {resp.status_code}",
                status_code=resp.status_code,
                payload=payload,
            )
        if isinstance(payload, dict) and payload.get("error"):
            raise AvataError(str(payload.get("error")), payload=payload)
        return payload if isinstance(payload, dict) else {"data": payload}

    def create_accounts(self, count: int = 1, operation_id: str | None = None) -> dict[str, Any]:
        op = operation_id or self.new_operation_id("acct")
        return self.request("POST", "/v3/accounts", data={"count": count, "operation_id": op})

    def create_nft_class(
        self,
        name: str,
        *,
        owner: str,
        symbol: str = "WC26",
        description: str = "",
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        op = operation_id or self.new_operation_id("class")
        return self.request(
            "POST",
            "/v3/native/nft/classes",
            data={
                "name": name,
                "symbol": symbol,
                "description": description or "最后一舞 · 世界杯2026 球星数字藏品",
                "owner": owner,
                "operation_id": op,
            },
        )

    def mint_nft(
        self,
        class_id: str,
        *,
        name: str,
        uri: str,
        recipient: str,
        operation_id: str | None = None,
        data: str = "",
        uri_hash: str = "",
    ) -> dict[str, Any]:
        op = operation_id or self.new_operation_id("mint")
        return self.request(
            "POST",
            f"/v3/native/nft/nfts/{class_id}",
            data={
                "name": name,
                "uri": uri,
                "uri_hash": uri_hash,
                "data": data,
                "recipient": recipient,
                "operation_id": op,
            },
        )

    def transfer_nft(
        self,
        class_id: str,
        nft_id: str,
        *,
        owner: str,
        recipient: str,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """托管账户间 NFT 转移（合规转赠/二级成交结算用）。

        owner/recipient 均为平台托管的文昌链地址，平台先在服务端校验合规规则后再调链。
        """
        op = operation_id or self.new_operation_id("xfer")
        return self.request(
            "POST",
            f"/v3/native/nft/nfts/{class_id}/{owner}/{nft_id}",
            data={"recipient": recipient, "operation_id": op},
        )

    def query_tx(self, operation_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v3/native/tx/{operation_id}")

    def _mock_response(self, method: str, path: str, data: dict[str, Any]) -> dict[str, Any]:
        op = data.get("operation_id") or self.new_operation_id("mock")
        if path == "/v3/accounts" and method == "POST":
            addr = f"mock{uuid.uuid4().hex[:38]}"
            return {
                "data": {
                    "addresses": [{"native_address": addr, "hex_address": f"0x{uuid.uuid4().hex}"}],
                    "operation_id": op,
                }
            }
        if path == "/v3/native/nft/classes" and method == "POST":
            return {
                "data": {
                    "class_id": f"mock_class_{uuid.uuid4().hex[:16]}",
                    "operation_id": op,
                }
            }
        if path.startswith("/v3/native/nft/nfts/") and method == "POST":
            segments = [s for s in path.split("/") if s]
            # mint: /v3/native/nft/nfts/{class_id}
            # transfer: /v3/native/nft/nfts/{class_id}/{owner}/{nft_id}
            class_id = segments[4] if len(segments) > 4 else "mock_class"
            return {
                "data": {
                    "operation_id": op,
                    "class_id": class_id,
                    "nft_id": f"mock_nft_{uuid.uuid4().hex[:12]}",
                }
            }
        if path.startswith("/v3/native/tx/") and method == "GET":
            return {
                "data": {
                    "status": 1,
                    "tx_hash": f"mock_tx_{uuid.uuid4().hex[:16]}",
                    "message": "success",
                    "nft": {
                        "mint": {
                            "id": f"mock_nft_{uuid.uuid4().hex[:12]}",
                            "class_id": self.settings.avata_nft_class_id or "mock_class",
                        }
                    },
                }
            }
        return {"data": {"operation_id": op, "mock": True}}
