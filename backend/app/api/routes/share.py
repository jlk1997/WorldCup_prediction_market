"""Public HTML share pages for WeChat / crawler OG tags."""

from html import escape as html_escape

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.referral_service import ReferralService

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


@router.get("/share/invite", response_class=HTMLResponse)
def invite_share_page(
    ref: str = Query("", min_length=0, max_length=32),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    code = (ref or "").strip().upper()
    redirect_path = f"{base}/login?ref={code}" if code else f"{base}/login"

    preview = ReferralService(db, settings).preview_invite_code(code) if code else {"valid": False}
    image = f"{base}/share-og.png"

    if preview.get("valid"):
        nick = preview.get("inviter_nickname") or "好友"
        bonus = preview.get("register_invitee_bonus") or 0
        title = f"{nick} 邀请你加入最后一舞"
        description = f"2026 世界杯球迷互动 · 新用户注册得球迷币（含邀请奖励 +{bonus}）"
        url = f"{base}/share/invite?ref={code}"
    else:
        title = "最后一舞：世界杯2026"
        description = "2026 世界杯球迷互动 — 竞猜、AI 分析、擂台与排行榜"
        url = f"{base}/share/invite"

    return HTMLResponse(
        _share_html(
            title=title,
            description=description,
            url=url,
            image=image,
            redirect_path=redirect_path,
        )
    )
