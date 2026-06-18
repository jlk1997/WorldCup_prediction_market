"""Download team flags + legend portraits for collectible cards.

Sources:
  - Team flags: https://flagcdn.com (public flag CDN)
  - Legends: Wikimedia Commons API (CC-licensed photos)

Writes assets to frontend/public/flags and frontend/public/legends,
updates teams.logo_url and collectible_cards.image_url, then invalidates cache.

Usage:
  cd backend
  python -m scripts.fetch_collectible_images
  python -m scripts.fetch_collectible_images --force --force-cards
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.data.collectible_catalog import build_card_catalog
from app.data.flag_codes import COUNTRY_CODE_TO_FLAGCDN, LEGEND_WIKIMEDIA_FILES
from app.db.models import Team
from app.db.models.commerce import CollectibleCard
from app.db.session import SessionLocal
from app.services.collectible_service import invalidate_collectible_catalog_cache

FLAGS_DIR = REPO_ROOT / "frontend" / "public" / "flags"
LEGENDS_DIR = REPO_ROOT / "frontend" / "public" / "legends"
FLAG_WIDTH = 160
USER_AGENT = "WC2026Bot/1.0 (https://loveaibaby.cn; internal collectible image sync)"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"


def _save_image(raw: bytes, dest_webp: Path) -> Path:
    """Save as WebP; fall back to PNG beside dest_webp if Pillow missing."""
    try:
        from PIL import Image

        img = Image.open(BytesIO(raw)).convert("RGBA")
        dest_webp.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest_webp, "WEBP", quality=82, method=6)
        return dest_webp
    except ImportError:
        dest_png = dest_webp.with_suffix(".png")
        dest_png.parent.mkdir(parents=True, exist_ok=True)
        dest_png.write_bytes(raw)
        return dest_png


def _public_path(file_path: Path, public_dir: Path) -> str:
    rel = file_path.relative_to(public_dir.parent)
    return "/" + rel.as_posix()


def _download(url: str, timeout: float = 45.0) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content


def _wikimedia_thumb(file_title: str, width: int = 480) -> str | None:
    import json

    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": width,
        "format": "json",
    }
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=45.0, follow_redirects=True, headers=headers) as client:
        resp = client.get(WIKIMEDIA_API, params=params)
        resp.raise_for_status()
        payload = resp.json()
    for page in payload.get("query", {}).get("pages", {}).values():
        if page.get("missing"):
            return None
        info = (page.get("imageinfo") or [{}])[0]
        return info.get("thumburl") or info.get("url")
    return None


def fetch_team_flags(*, force: bool = False) -> dict[str, str]:
    """Return country_code -> public path (/flags/xxx.webp|.png)."""
    FLAGS_DIR.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    missing: list[str] = []

    for code, flagcdn in COUNTRY_CODE_TO_FLAGCDN.items():
        dest_webp = FLAGS_DIR / f"{code.lower()}.webp"
        dest_png = FLAGS_DIR / f"{code.lower()}.png"
        existing = dest_webp if dest_webp.exists() else (dest_png if dest_png.exists() else None)
        if existing and not force:
            mapping[code] = _public_path(existing, FLAGS_DIR)
            continue
        url = f"https://flagcdn.com/w{FLAG_WIDTH}/{flagcdn}.png"
        try:
            raw = _download(url)
            saved = _save_image(raw, dest_webp)
            mapping[code] = _public_path(saved, FLAGS_DIR)
            print(f"  flag OK {code} -> {saved.name}")
        except Exception as exc:
            missing.append(code)
            print(f"  flag FAIL {code} ({flagcdn}): {exc}")

    if missing:
        print(f"warn: {len(missing)} flags failed: {', '.join(missing)}")
    return mapping


def fetch_legend_portraits(*, force: bool = False) -> dict[str, str]:
    """Return legend key -> public path (/legends/name.webp|.png)."""
    LEGENDS_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, str] = {}
    for name, file_title in LEGEND_WIKIMEDIA_FILES.items():
        dest_webp = LEGENDS_DIR / f"{name}.webp"
        dest_png = LEGENDS_DIR / f"{name}.png"
        existing = dest_webp if dest_webp.exists() else (dest_png if dest_png.exists() else None)
        if existing and not force:
            out[name] = _public_path(existing, LEGENDS_DIR)
            continue
        try:
            thumb = _wikimedia_thumb(file_title)
            if not thumb:
                print(f"  legend FAIL {name}: Wikimedia file not found")
                continue
            raw = _download(thumb)
            saved = _save_image(raw, dest_webp)
            out[name] = _public_path(saved, LEGENDS_DIR)
            print(f"  legend OK {name} -> {saved.name}")
        except Exception as exc:
            print(f"  legend FAIL {name}: {exc}")
    return out


def apply_to_database(*, force_cards: bool = False) -> dict[str, int]:
    db = SessionLocal()
    stats = {"teams_updated": 0, "cards_updated": 0}
    try:
        for team in db.query(Team).all():
            code = (team.country_code or "").upper()
            if code not in COUNTRY_CODE_TO_FLAGCDN:
                print(f"warn: no flag mapping for team {team.name} ({code})")
                continue
            flag_webp = FLAGS_DIR / f"{code.lower()}.webp"
            flag_png = FLAGS_DIR / f"{code.lower()}.png"
            flag_file = flag_webp if flag_webp.exists() else (flag_png if flag_png.exists() else None)
            if not flag_file:
                continue
            logo_url = _public_path(flag_file, FLAGS_DIR)
            if team.logo_url != logo_url:
                team.logo_url = logo_url
                stats["teams_updated"] += 1

        card_defs, _ = build_card_catalog(db)
        url_by_code = {c["code"]: c.get("image_url") for c in card_defs if c.get("image_url")}
        for row in db.query(CollectibleCard).filter(CollectibleCard.active.is_(True)).all():
            url = url_by_code.get(row.code)
            if not url:
                continue
            if force_cards or not row.image_url:
                if row.image_url != url:
                    row.image_url = url
                    stats["cards_updated"] += 1

        db.commit()
        invalidate_collectible_catalog_cache()
    finally:
        db.close()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Fetch collectible card images")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    parser.add_argument(
        "--force-cards",
        action="store_true",
        help="Overwrite collectible_cards.image_url even when already set",
    )
    parser.add_argument("--skip-download", action="store_true", help="Only apply DB from existing files")
    args = parser.parse_args()

    print("→ Downloading team flags (flagcdn.com)...")
    if not args.skip_download:
        fetch_team_flags(force=args.force)
        print("→ Downloading legend portraits (Wikimedia API)...")
        fetch_legend_portraits(force=args.force)
    else:
        print("skip download, using existing files")

    print("→ Updating database (teams.logo_url + collectible_cards.image_url)...")
    stats = apply_to_database(force_cards=args.force_cards or args.force)
    flag_count = len(list(FLAGS_DIR.glob("*.webp"))) + len(list(FLAGS_DIR.glob("*.png")))
    legend_count = len(list(LEGENDS_DIR.glob("*.webp"))) + len(list(LEGENDS_DIR.glob("*.png")))
    print(
        {
            "teams_updated": stats["teams_updated"],
            "cards_updated": stats["cards_updated"],
            "flag_files": flag_count,
            "legend_files": legend_count,
        }
    )
    print("\n[OK] Done. Next: cd frontend && npm run build && deploy dist")


if __name__ == "__main__":
    main()
