"""Parse predict-settled notification body when payload fields are missing."""

from __future__ import annotations

import re
from typing import Any

_MATCH_BODY = re.compile(r"^(.+?)\s+vs\s+(.+?)\s+比分\s*(\d+:\d+)", re.IGNORECASE)
_MATCH_LABEL = re.compile(r"^(.+?)\s+vs\s+(.+?)$", re.IGNORECASE)
_SCORE_IN_BODY = re.compile(r"比分\s*(\d+:\d+)")


def parse_teams_from_body(body: str | None) -> tuple[str | None, str | None]:
    if not body:
        return None, None
    m = _MATCH_BODY.match(body.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, None


def parse_score_from_body(body: str | None) -> str | None:
    if not body:
        return None
    m = _SCORE_IN_BODY.search(body)
    return m.group(1) if m else None


def enrich_predict_payload(payload: dict[str, Any] | None, body: str | None) -> dict[str, Any]:
    data = dict(payload or {})
    team1 = data.get("team1") or data.get("team1_name")
    team2 = data.get("team2") or data.get("team2_name")
    if not team1 or not team2:
        parsed1, parsed2 = parse_teams_from_body(body)
        if parsed1 and parsed2:
            data.setdefault("team1", parsed1)
            data.setdefault("team2", parsed2)
    if not data.get("final_score"):
        score = parse_score_from_body(body)
        if score:
            data.setdefault("final_score", score)
    t1 = data.get("team1")
    t2 = data.get("team2")
    if t1 and t2 and not data.get("match_label"):
        data["match_label"] = f"{t1} vs {t2}"
    return data
