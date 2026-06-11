from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ChannelCursor(SQLModel, table=True):
    channel_username: str = Field(primary_key=True)
    last_message_id: int = Field(default=0)
    # >0：尚需回填更早消息（max_id=history_min_id）；0 表示历史已扫完
    history_min_id: int = Field(default=0)


class Link(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    category: str = Field(default="未分类", index=True)
    channel_username: str = Field(index=True)
    message_id: int = Field(index=True)
    tags: str = Field(default="", description="Comma-separated hashtags from source message")
    source_text: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
