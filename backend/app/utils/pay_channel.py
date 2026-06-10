"""Resolve Alipay page vs WAP pay channel."""

from typing import Literal

PayChannel = Literal["page", "wap"]
PayChannelRequest = Literal["auto", "page", "wap"]


def is_mobile_user_agent(user_agent: str | None) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return False
    if "ipad" in ua or "tablet" in ua:
        return False
    return any(token in ua for token in ("mobile", "android", "iphone", "ipod"))


def resolve_pay_channel(requested: PayChannelRequest, user_agent: str | None = None) -> PayChannel:
    if requested == "page":
        return "page"
    if requested == "wap":
        return "wap"
    return "wap" if is_mobile_user_agent(user_agent) else "page"
