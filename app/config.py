import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_PORT = 8765


def _on_cloud() -> bool:
    return bool(
        os.getenv("RENDER")
        or os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("FLY_APP_NAME")
        or (os.getenv("PORT") and os.getenv("PORT") != str(DEV_PORT))
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_api_id: int = 0
    telegram_api_hash: str = ""

    telegram_bot_token: str | None = Field(default=None)
    telegram_session_string: str | None = Field(
        default=None,
        description="Telethon StringSession，适合部署；本地也可用文件会话",
    )
    telegram_session_file: str = Field(
        default="data/user_session",
        description="无 StringSession 时使用该路径（不含 .session 后缀，由 Telethon 生成文件）",
    )

    telegram_proxy: str | None = Field(default=None)

    telegram_channels: str = ""
    admin_sync_token: str = "change-me"

    database_path: str = "data/nav.db"
    host: str = "127.0.0.1"
    port: int = DEV_PORT

    enable_daily_sync: bool = True
    daily_sync_time: str = "09:00"

    sync_batch_size: int = Field(default=200, description="每批拉取消息条数")
    sync_backfill_batches: int = Field(default=10, description="单次 sync 最多回填几批历史")
    sync_on_startup: bool = Field(
        default=False,
        description="库为空时启动后自动采集；云端默认开启，可用 SYNC_ON_STARTUP=false 关闭",
    )

    @field_validator("port")
    @classmethod
    def _port_fixed_local(cls, v: int) -> int:
        if _on_cloud():
            return v
        if v != DEV_PORT:
            raise ValueError(
                f"本地开发固定端口 {DEV_PORT}，请勿修改 .env 中的 PORT。"
                "若端口占用请运行 scripts/free_port.ps1。"
            )
        return v

    @model_validator(mode="after")
    def _cloud_bind(self) -> "Settings":
        if _on_cloud():
            self.host = "0.0.0.0"
            if os.getenv("PORT"):
                self.port = int(os.getenv("PORT"))
            if os.getenv("SYNC_ON_STARTUP") is None:
                self.sync_on_startup = True
        return self

    @field_validator("telegram_session_string", mode="before")
    @classmethod
    def _normalize_session_string(cls, v: object) -> str | None:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            return None
        s = "".join(v.split())
        return s or None

    @model_validator(mode="before")
    @classmethod
    def _empty_env_to_none(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        for key in ("telegram_bot_token", "telegram_session_string", "telegram_proxy"):
            if data.get(key) == "":
                data[key] = None
        return data

    def channel_list(self) -> list[str]:
        return [c.strip().lstrip("@") for c in self.telegram_channels.split(",") if c.strip()]

    def use_bot_session(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_bot_token.strip())


settings = Settings()
