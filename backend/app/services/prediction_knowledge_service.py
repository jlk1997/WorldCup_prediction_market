"""Load WC2026 prediction knowledge base for DataAgent context."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import REPO_ROOT, get_settings

_STAGE_HEADINGS = {
    "group": ("小组赛", "小组", "GROUP"),
    "knockout": ("淘汰赛", "十六强", "八分之一", "四分之一", "半决赛", "1/8", "1/4"),
    "final": ("决赛", "FINAL", "冠军"),
}


@lru_cache(maxsize=1)
def load_knowledge_text() -> str:
    settings = get_settings()
    path = Path(settings.prediction_knowledge_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        return ""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    return raw.strip()[:8000]


def _stage_from_match(match: Any | None) -> str:
    if match is None:
        return "group"
    round_type = (getattr(match, "round_type", None) or "group").lower()
    bracket = (getattr(match, "bracket_round", None) or "").lower()
    if round_type == "final" or "final" in bracket:
        return "final"
    if round_type in ("knockout", "playoff") or bracket:
        return "knockout"
    return "group"


def _lines_for_stage(full: str, stage: str) -> list[str]:
    keywords = _STAGE_HEADINGS.get(stage, _STAGE_HEADINGS["group"])
    picked: list[str] = []
    for line in full.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(kw in stripped for kw in keywords):
            picked.append(stripped)
    if picked:
        return picked[:14]
    if stage == "final":
        return [ln.strip() for ln in full.splitlines() if ln.strip()][:10]
    if stage == "knockout":
        mid = len(full.splitlines()) // 3
        return [ln.strip() for ln in full.splitlines()[mid : mid + 12] if ln.strip()]
    return [ln.strip() for ln in full.splitlines()[:18] if ln.strip()]


def snippet_for_teams(
    team1: str,
    team2: str,
    *,
    max_len: int = 1200,
    match: Any | None = None,
    stage: str | None = None,
) -> str:
    """Return relevant excerpt for a matchup (team names + bracket stage context)."""
    full = load_knowledge_text()
    if not full:
        return ""
    stage_key = stage or _stage_from_match(match)
    names = {team1.strip(), team2.strip()}
    lines: list[str] = []
    for line in full.splitlines():
        if any(n and n in line for n in names if n):
            lines.append(line.strip())
    if lines:
        body = "\n".join(lines[:12])
    else:
        stage_lines = _lines_for_stage(full, stage_key)
        body = "\n".join(stage_lines)
    stage_label = {"group": "小组赛", "knockout": "淘汰赛", "final": "决赛"}.get(stage_key, "")
    disclaimer = "（第三方计量模型参考，非官方赛果，仅供 AI 娱乐分析）"
    prefix = f"[{stage_label}] " if stage_label else ""
    text = f"{prefix}{body}\n{disclaimer}"
    return text[:max_len]


def snippet_for_match(match: Any, *, max_len: int = 1200) -> str:
    return snippet_for_teams(
        getattr(match, "team1_name", "") or "",
        getattr(match, "team2_name", "") or "",
        max_len=max_len,
        match=match,
    )
