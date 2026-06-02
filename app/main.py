from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.classify import infer_category
from app.message_parse import parse_resource_title_desc
from app.config import settings
from app.daily_scheduler import start_daily_sync_task
from app.database import get_session, init_db
from app.models import Link
from app.sync import sync_channels

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str
    description: str
    category: str
    channel_username: str
    message_id: int
    tags: str
    created_at: datetime


class CategoryCount(BaseModel):
    name: str
    count: int


def _verify_sync_token(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.admin_sync_token}"
    if not authorization or authorization.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization bearer token")


app = FastAPI(title="TG Nav Hub", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    STATIC.mkdir(parents=True, exist_ok=True)
    start_daily_sync_task()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "api": "2"}


@app.get("/api/categories", response_model=list[CategoryCount])
def list_categories(session: Session = Depends(get_session)) -> list[CategoryCount]:
    cnt = func.count(Link.id).label("cnt")
    stmt = select(Link.category, cnt).group_by(Link.category).order_by(cnt.desc())
    rows = session.exec(stmt).all()
    return [CategoryCount(name=r[0] or "未分类", count=int(r[1])) for r in rows]


@app.get("/api/links", response_model=list[LinkOut])
def list_links(
    q: str | None = Query(default=None, description="Search title, url, tags, category"),
    category: str | None = Query(default=None, description="Filter by category name"),
    session: Session = Depends(get_session),
) -> list[LinkOut]:
    stmt = select(Link).order_by(Link.created_at.desc())
    if category:
        stmt = stmt.where(Link.category == category.strip())
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Link.title.like(pattern),
                Link.url.like(pattern),
                Link.tags.like(pattern),
                Link.description.like(pattern),
                Link.category.like(pattern),
            )
        )
    rows = list(session.exec(stmt).all())
    return [LinkOut.model_validate(row) for row in rows]


@app.post("/api/sync")
async def trigger_sync(_: None = Depends(_verify_sync_token)) -> dict:
    from app.daily_scheduler import run_scheduled_sync

    return await run_scheduled_sync()


@app.get("/api/sync/status")
def sync_status() -> dict:
    path = ROOT / "data" / "last_sync.json"
    if not path.is_file():
        return {"last": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"last": None, "error": "invalid last_sync.json"}


@app.post("/api/reclassify")
def reclassify_all(_: None = Depends(_verify_sync_token), session: Session = Depends(get_session)) -> dict[str, int]:
    """重算分类，并按 source_text 修正资源名与简介（需 Bearer）。"""
    links = session.exec(select(Link)).all()
    updated = 0
    for link in links:
        changed = False
        if link.source_text:
            title, desc = parse_resource_title_desc(link.source_text)
            if title and link.title != title:
                link.title = title
                changed = True
            if desc and link.description != desc:
                link.description = desc
                changed = True
        nc = infer_category(link.url, link.tags or "", link.title or "")
        if link.category != nc:
            link.category = nc
            changed = True
        if changed:
            updated += 1
    if updated:
        session.commit()
    return {"updated": updated}


@app.get("/")
def spa_index() -> FileResponse:
    index = STATIC / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="static/index.html missing")
    return FileResponse(index)


