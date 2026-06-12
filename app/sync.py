from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlmodel import Session, select
from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.sessions import StringSession

from app.classify import extract_hashtags, infer_category, tags_to_csv
from app.message_parse import parse_resource_title_desc
from app.config import settings
from app.database import _engine
from app.models import ChannelCursor, Link
from app.tg_connect import create_client

URL_RE = re.compile(r"https?://[^\s<>\]\[\"'\)]+", re.IGNORECASE)
def _normalize_url(raw: str) -> str:
    return raw.strip().rstrip(").,]'\"»」』）}.")


def _extract_urls(text: str) -> list[str]:
    if not text:
        return []
    found = URL_RE.findall(text)
    return [_normalize_url(u) for u in found if _is_reasonable_url(u)]


def _is_reasonable_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return bool(p.netloc and p.scheme in ("http", "https"))
    except Exception:
        return False


async def _connect_client() -> TelegramClient:
    """Bot：频道管理员场景。用户会话：可读公开频道（含他人频道），无需管理员权限。"""
    api_id = settings.telegram_api_id
    api_hash = settings.telegram_api_hash

    if not api_id or not (api_hash or "").strip():
        raise RuntimeError("请先在 .env 填写 TELEGRAM_API_ID 与 TELEGRAM_API_HASH（https://my.telegram.org/apps）。")

    if settings.use_bot_session():
        client = create_client("data/tg_bot_session", api_id, api_hash)
        await client.start(bot_token=settings.telegram_bot_token)
        return client

    if settings.telegram_session_string:
        sess: StringSession | str = StringSession(settings.telegram_session_string)
    else:
        sess_file = Path(f"{settings.telegram_session_file}.session")
        if not sess_file.is_file():
            raise RuntimeError(
                "未设置 TELEGRAM_SESSION_STRING，且找不到会话文件 "
                f"{sess_file.as_posix()}。请在项目根目录运行 "
                "`py scripts/login_telegram.py` 登录，并把输出的会话字符串写入 .env。"
            )
        sess = settings.telegram_session_file

    client = create_client(sess, api_id, api_hash)
    await client.start()

    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram 用户会话未授权：请在项目根目录运行 "
            "`py scripts/login_telegram.py` 登录并写入 TELEGRAM_SESSION_STRING，"
            "或确保已生成本地会话文件。"
        )
    return client


async def sync_channels() -> dict:
    channels = settings.channel_list()
    if not channels:
        return {
            "channels": 0,
            "new_links": 0,
            "messages_seen": 0,
            "errors": ["请在 .env 中配置 TELEGRAM_CHANNELS（多个用户名用英文逗号分隔，不要 @）。"],
        }

    try:
        client = await _connect_client()
    except RuntimeError as e:
        return {"channels": 0, "new_links": 0, "messages_seen": 0, "errors": [str(e)]}
    except Exception as e:  # noqa: BLE001
        return {
            "channels": 0,
            "new_links": 0,
            "messages_seen": 0,
            "errors": [f"连接 Telegram 失败：{e.__class__.__name__}: {e}"],
        }

    stats = {
        "channels": 0,
        "new_links": 0,
        "messages_seen": 0,
        "history_messages_seen": 0,
        "errors": [],
    }

    try:
        with Session(_engine) as session:
            for username in channels:
                try:
                    ch_stats = await _sync_one_channel(client, session, username)
                    stats["channels"] += 1
                    stats["new_links"] += ch_stats["new_links"]
                    stats["messages_seen"] += ch_stats["messages_seen"]
                    stats["history_messages_seen"] += ch_stats["history_messages_seen"]
                except RPCError as e:
                    stats["errors"].append(f"{username}: {e.__class__.__name__}: {e}")
                except Exception as e:  # noqa: BLE001
                    stats["errors"].append(f"{username}: {e.__class__.__name__}: {e}")
            session.commit()
    finally:
        await client.disconnect()

    return stats



def _msg_posted_at(msg) -> datetime:
    posted = getattr(msg, "date", None)
    if posted is None:
        return datetime.utcnow()
    if posted.tzinfo is not None:
        return posted.astimezone(timezone.utc).replace(tzinfo=None)
    return posted


def _process_messages(
    session: Session, username: str, messages: list
) -> tuple[int, int, int | None, int | None]:
    new_links = 0
    seen = 0
    min_id: int | None = None
    max_id: int | None = None

    for msg in messages:
        seen += 1
        if not msg.id:
            continue
        min_id = msg.id if min_id is None else min(min_id, msg.id)
        max_id = msg.id if max_id is None else max(max_id, msg.id)
        text = (getattr(msg, "text", None) or getattr(msg, "message", None) or "") or ""
        if not text.strip():
            continue

        urls = _extract_urls(text)
        if not urls:
            continue

        title_base, desc_base = parse_resource_title_desc(text)
        tags = tags_to_csv(extract_hashtags(text))

        posted_at = _msg_posted_at(msg)
        for url in urls:
            exists = session.exec(select(Link).where(Link.url == url)).first()
            if exists:
                if exists.created_at != posted_at:
                    exists.created_at = posted_at
                continue
            link = Link(
                url=url,
                title=title_base or url,
                description=desc_base,
                category=infer_category(url, tags, title_base),
                channel_username=username,
                message_id=msg.id,
                tags=tags,
                source_text=text[:2000],
                created_at=posted_at,
            )
            session.add(link)
            new_links += 1

    return new_links, seen, min_id, max_id


async def _sync_one_channel(client: TelegramClient, session: Session, username: str) -> dict:
    batch = settings.sync_batch_size
    cursor = session.get(ChannelCursor, username)
    if cursor is None:
        cursor = ChannelCursor(channel_username=username, last_message_id=0, history_min_id=0)
        session.add(cursor)
        session.commit()
        session.refresh(cursor)

    last_id = cursor.last_message_id
    if last_id == 0:
        messages = await client.get_messages(username, limit=batch)
    else:
        messages = await client.get_messages(username, min_id=last_id, limit=batch)

    new_links, seen, min_id, max_id = _process_messages(session, username, messages)
    if max_id is not None:
        cursor.last_message_id = max(max_id, cursor.last_message_id)
    if min_id is not None and cursor.history_min_id == 0:
        cursor.history_min_id = min_id

    history_seen = 0
    for _ in range(max(settings.sync_backfill_batches, 0)):
        if cursor.history_min_id <= 0:
            break
        older = await client.get_messages(username, max_id=cursor.history_min_id, limit=batch)
        if not older:
            cursor.history_min_id = 0
            break
        batch_new, batch_seen, batch_min, _ = _process_messages(session, username, older)
        new_links += batch_new
        history_seen += batch_seen
        if batch_min is None:
            cursor.history_min_id = 0
            break
        cursor.history_min_id = batch_min

    session.add(cursor)
    session.commit()

    return {
        "new_links": new_links,
        "messages_seen": seen,
        "history_messages_seen": history_seen,
    }


async def refresh_posted_times() -> dict:
    """按 Telegram 消息时间修正 created_at，便于按发布时间排序展示。"""
    channels = settings.channel_list()
    if not channels:
        return {"channels": 0, "updated": 0, "errors": ["未配置 TELEGRAM_CHANNELS"]}

    try:
        client = await _connect_client()
    except RuntimeError as e:
        return {"channels": 0, "updated": 0, "errors": [str(e)]}
    except Exception as e:  # noqa: BLE001
        return {
            "channels": 0,
            "updated": 0,
            "errors": [f"连接 Telegram 失败：{e.__class__.__name__}: {e}"],
        }

    stats = {"channels": 0, "updated": 0, "errors": []}
    try:
        with Session(_engine) as session:
            for username in channels:
                try:
                    stats["channels"] += 1
                    stats["updated"] += await _refresh_channel_posted_times(client, session, username)
                except RPCError as e:
                    stats["errors"].append(f"{username}: {e.__class__.__name__}: {e}")
                except Exception as e:  # noqa: BLE001
                    stats["errors"].append(f"{username}: {e.__class__.__name__}: {e}")
            session.commit()
    finally:
        await client.disconnect()

    return stats


async def _refresh_channel_posted_times(
    client: TelegramClient, session: Session, username: str
) -> int:
    links = list(
        session.exec(
            select(Link)
            .where(Link.channel_username == username)
            .order_by(Link.message_id.desc())
        ).all()
    )
    if not links:
        return 0

    updated = 0
    chunk_size = 100
    for i in range(0, len(links), chunk_size):
        chunk_links = links[i : i + chunk_size]
        messages = await client.get_messages(username, ids=[link.message_id for link in chunk_links])
        by_id = {msg.id: msg for msg in messages if msg and msg.id}
        for link in chunk_links:
            msg = by_id.get(link.message_id)
            if not msg:
                continue
            posted_at = _msg_posted_at(msg)
            if link.created_at != posted_at:
                link.created_at = posted_at
                updated += 1
    return updated
