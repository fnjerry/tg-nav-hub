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
    """旧库补充缺失列。"""
    with _engine.begin() as conn:
        link_rows = conn.execute(text("PRAGMA table_info(link)")).fetchall()
        if link_rows:
            link_cols = {r[1] for r in link_rows}
            if "category" not in link_cols:
                conn.execute(text("ALTER TABLE link ADD COLUMN category VARCHAR DEFAULT '未分类'"))
                conn.execute(text("UPDATE link SET category = '未分类' WHERE category IS NULL"))

        cursor_rows = conn.execute(text("PRAGMA table_info(channelcursor)")).fetchall()
        if cursor_rows:
            cursor_cols = {r[1] for r in cursor_rows}
            if "history_min_id" not in cursor_cols:
                conn.execute(
                    text("ALTER TABLE channelcursor ADD COLUMN history_min_id INTEGER DEFAULT 0")
                )
                conn.execute(
                    text(
                        "UPDATE channelcursor SET history_min_id = last_message_id "
                        "WHERE last_message_id > 0 AND history_min_id = 0"
                    )
                )


def init_db() -> None:
    SQLModel.metadata.create_all(_engine)
    _migrate_sqlite()


def get_session():
    with Session(_engine) as session:
        yield session
