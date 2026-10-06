from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_telegram_id: int | None = None
    database_url: str = "sqlite+aiosqlite:///./clientflow.db"
    admin_web_username: str = "admin"
    admin_web_password: str = "change_me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()

        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]

        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]

        return url


settings = Settings()
