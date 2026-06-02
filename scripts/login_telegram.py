"""
一次性登录：用你的手机号生成 Telethon 会话，供采集公开频道使用。

用法（在项目根目录）：
  py scripts/login_telegram.py

成功后把输出的 TELEGRAM_SESSION_STRING=... 整行粘贴进 .env。
切勿泄露该字符串（等同于账号登录态）。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telethon.sessions import StringSession  # noqa: E402

from app.config import settings  # noqa: E402
from app.tg_connect import create_client  # noqa: E402


async def main() -> None:
    if not settings.telegram_api_id or not (settings.telegram_api_hash or "").strip():
        print("请先在项目根目录创建 .env，并填写 TELEGRAM_API_ID、TELEGRAM_API_HASH（https://my.telegram.org/apps）。")
        sys.exit(1)
    Path("data").mkdir(parents=True, exist_ok=True)
    session = StringSession()
    client = create_client(session, settings.telegram_api_id, settings.telegram_api_hash)
    if settings.telegram_proxy:
        print(f"已启用代理：{settings.telegram_proxy}")
        try:
            import python_socks  # noqa: F401
        except ImportError:
            print("错误：未安装 python-socks，代理会被 Telethon 忽略。请执行：pip install \"python-socks[asyncio]\"")
            sys.exit(1)
    else:
        print("提示：若出现 TimeoutError，请在 .env 设置 TELEGRAM_PROXY（见 .env.example）。")
    print("按提示输入手机号与验证码（Telegram 官方登录流程）…")
    try:
        await client.start()
    except TimeoutError:
        print(
            "\n连接 Telegram 超时。常见原因：网络无法直连 Telegram。\n"
            "请在 .env 增加一行本地代理，例如（端口按你本机 Clash / v2rayN 为准）：\n"
            "  TELEGRAM_PROXY=socks5://127.0.0.1:7890\n"
            "若仍失败，可尝试：TELEGRAM_PROXY=socks5h://127.0.0.1:7890\n"
        )
        raise
    except OSError as e:
        if getattr(e, "winerror", None) == 121 or "121" in str(e):
            print(
                "\n[WinError 121] 信号灯超时：通常表示 **到代理地址的 TCP 连不上** 或 **代理未开 SOCKS 口**。\n"
                "请在 PowerShell 检查（把 IP、端口换成你的）：\n"
                "  Test-NetConnection 192.168.50.5 -Port 7890\n"
                "若 TcpTestSucceeded 为 False：检查该局域网 IP 是否在线、Clash 是否开启「允许局域网连接」、端口是否为 SOCKS 而非仅 HTTP。\n"
                "代理在本机时可改为：TELEGRAM_PROXY=socks5://127.0.0.1:7890\n"
            )
        raise
    try:
        line = client.session.save()
        print("\n将下面这一行加入 .env（勿提交到 git）：")
        print(f"TELEGRAM_SESSION_STRING={line}\n")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
