"""Public HTML share pages for WeChat / crawler OG tags."""

from html import escape as html_escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.share_page_service import SharePageService

router = APIRouter(tags=["share"])


def _share_html(
    *,
    title: str,
    description: str,
    url: str,
    image: str,
    redirect_path: str,
) -> str:
    safe_title = html_escape(title)
    safe_desc = html_escape(description)
    safe_url = html_escape(url)
    safe_image = html_escape(image)
    safe_redirect = html_escape(redirect_path)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{safe_title}</title>
  <meta name="description" content="{safe_desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="最后一舞" />
  <meta property="og:title" content="{safe_title}" />
  <meta property="og:description" content="{safe_desc}" />
  <meta property="og:url" content="{safe_url}" />
  <meta property="og:image" content="{safe_image}" />
  <meta itemprop="name" content="{safe_title}" />
  <meta itemprop="description" content="{safe_desc}" />
  <meta itemprop="image" content="{safe_image}" />
  <meta http-equiv="refresh" content="0;url={safe_redirect}" />
</head>
<body>
  <p>{safe_desc}</p>
  <p><a href="{safe_redirect}">点击进入最后一舞</a></p>
  <script>location.replace("{safe_redirect}");</script>
</body>
</html>"""


def _render_page(svc: SharePageService, meta: dict | None) -> HTMLResponse:
    settings = svc.settings
    base = settings.frontend_base_url.rstrip("/")
    image = f"{base}/share-og.png"
    if not meta:
        meta = {
            "title": "最后一舞：世界杯2026",
            "description": "2026 世界杯球迷互动 — 竞猜、AI 分析、擂台与排行榜",
            "url": f"{base}/",
            "redirect_path": f"{base}/login",
        }
    return HTMLResponse(
        _share_html(
            title=meta["title"],
            description=meta["description"],
            url=meta["url"],
            image=image,
            redirect_path=meta["redirect_path"],
        )
    )


@router.get("/share/invite", response_class=HTMLResponse)
def invite_share_page(
    ref: str = Query("", min_length=0, max_length=32),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    code = (ref or "").strip().upper()
    svc = SharePageService(db, settings)
    return _render_page(svc, svc.invite_share_page(code))


@router.get("/share/predict/{prediction_id}", response_class=HTMLResponse)
def predict_share_page(prediction_id: int, db: Session = Depends(get_db)):
    settings = get_settings()
    svc = SharePageService(db, settings)
    return _render_page(svc, svc.predict_share_page(prediction_id))


@router.get("/share/card/{token}", response_class=HTMLResponse)
def card_share_page(token: str, db: Session = Depends(get_db)):
    settings = get_settings()
    svc = SharePageService(db, settings)
    return _render_page(svc, svc.card_share_page(token))


@router.get("/share/rank", response_class=HTMLResponse)
def rank_share_page(
    period: str = Query("season", max_length=20),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    svc = SharePageService(db, settings)
    return _render_page(svc, svc.rank_share_page(period))
