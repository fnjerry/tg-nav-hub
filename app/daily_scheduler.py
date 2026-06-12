"""本机每天固定时刻自动采集（需 uvicorn 常驻运行）。"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, time, timedelta, timezone

from sqlmodel import Session

from app.config import settings
from app.database import data_directory
from app.sync import sync_channels

logger = logging.getLogger("tg_nav_hub.scheduler")


def _parse_hhmm(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError("DAILY_SYNC_TIME 须为 HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("DAILY_SYNC_TIME 超出范围")
    return time(hour, minute)


def _seconds_until(target: time) -> float:
    now = datetime.now()
    run_at = datetime.combine(now.date(), target)
    if now >= run_at:
        run_at += timedelta(days=1)
    return (run_at - now).total_seconds()


def _save_result(result: dict) -> None:
    payload = {"at": datetime.now(timezone.utc).isoformat(), "result": result, "source": "scheduler"}
    (data_directory() / "last_sync.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def run_scheduled_sync() -> dict:
    result = await sync_channels()
    _save_result(result)
    logger.info(
        "daily sync done: new_links=%s messages_seen=%s errors=%s",
        result.get("new_links"),
        result.get("messages_seen"),
        result.get("errors"),
    )
    return result


async def daily_sync_loop() -> None:
    try:
        at = _parse_hhmm(settings.daily_sync_time)
    except ValueError as e:
        logger.warning("daily sync disabled: %s", e)
        return

    logger.info("daily sync scheduled at %s (local)", settings.daily_sync_time)
    while True:
        await asyncio.sleep(_seconds_until(at))
        try:
            await run_scheduled_sync()
        except Exception:
            logger.exception("daily sync failed")


async def startup_sync_if_empty() -> None:
    if not settings.sync_on_startup:
        return
    if not settings.channel_list():
        return
    if not settings.telegram_api_id or not (settings.telegram_api_hash or "").strip():
        return
    if not settings.use_bot_session() and not settings.telegram_session_string:
        return

    from sqlmodel import func, select

    from app.database import _engine
    from app.models import Link

    with Session(_engine) as session:
        count = session.exec(select(func.count()).select_from(Link)).one()
        if count > 0:
            return

    logger.info("startup: database empty, running initial sync")
    try:
        result = await run_scheduled_sync()
        logger.info(
            "startup sync done: new_links=%s history_messages_seen=%s errors=%s",
            result.get("new_links"),
            result.get("history_messages_seen"),
            result.get("errors"),
        )
    except Exception:
        logger.exception("startup sync failed")


def start_startup_sync_task() -> None:
    asyncio.create_task(startup_sync_if_empty())


def start_daily_sync_task() -> None:
    if not settings.enable_daily_sync:
        return
    asyncio.create_task(daily_sync_loop())
