from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

Path("data").mkdir(parents=True, exist_ok=True)

_engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)


def _migrate_sqlite() -> None:
    """旧库补充 link.category 列。"""
    with _engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(link)")).fetchall()
        if not rows:
            return
        cols = {r[1] for r in rows}
        if "category" not in cols:
            conn.execute(text("ALTER TABLE link ADD COLUMN category VARCHAR DEFAULT '未分类'"))
            conn.execute(text("UPDATE link SET category = '未分类' WHERE category IS NULL"))


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)
    _migrate_sqlite()


def get_session():
    with Session(_engine) as session:
        yield session
