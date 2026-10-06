from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_telegram_id: int | None = None
    database_url: str = "sqlite+aiosqlite:///./clientflow.db"
    admin_web_username: str = "admin"
    admin_web_password: str = "change_me"
    telegram_webhook_secret: str | None = None
    render_external_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()

        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]

        if not url.startswith("postgresql+asyncpg://"):
            return url

        parts = urlsplit(url)
        query = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in {"sslmode", "channel_binding"}
        ]

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

    @property
    def webhook_url(self) -> str | None:
        if not self.render_external_url:
            return None

        return f"{self.render_external_url.rstrip('/')}/telegram/webhook"


settings = Settings()
