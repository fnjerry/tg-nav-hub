"""TelegramClient 公共参数：代理、超时、重试。

Telethon 要求安装 python-socks（带 asyncio 额外依赖），否则 proxy 会被静默忽略。
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse

from python_socks import ProxyType
from telethon import TelegramClient

from app.config import settings


def _proxy_tuple(proxy_url: str | None) -> tuple | None:
    """将 socks5/http URL 转为 Telethon 接受的 tuple（与 python-socks / PySocks 数值兼容）。"""
    if not proxy_url or not str(proxy_url).strip():
        return None
    u = urlparse(str(proxy_url).strip())
    scheme = (u.scheme or "").lower()
    host = u.hostname or "127.0.0.1"
    port = u.port
    user = unquote(u.username) if u.username else None
    pwd = unquote(u.password) if u.password else None

    if scheme in ("socks5", "socks5h"):
        if port is None:
            port = 1080
        rdns = scheme == "socks5h"
        if user is not None or pwd is not None:
            return (ProxyType.SOCKS5, host, port, rdns, user, pwd)
        return (ProxyType.SOCKS5, host, port, rdns)

    if scheme == "socks4":
        if port is None:
            port = 1080
        return (ProxyType.SOCKS4, host, port)

    if scheme in ("http", "https"):
        if port is None:
            port = 8080
        if user is not None or pwd is not None:
            return (ProxyType.HTTP, host, port, True, user, pwd)
        return (ProxyType.HTTP, host, port)

    return None


def create_client(session, api_id: int, api_hash: str) -> TelegramClient:
    proxy = _proxy_tuple(settings.telegram_proxy)
    kw: dict = {
        "connection_retries": 15,
        "retry_delay": 3,
        "timeout": 120,
        "request_retries": 5,
    }
    if proxy:
        kw["proxy"] = proxy
    return TelegramClient(session, api_id, api_hash, **kw)
