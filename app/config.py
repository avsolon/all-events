from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "All Events Novosibirsk"
    DEBUG: bool = False
    DATABASE_URL: str = f"sqlite+aiosqlite:///{Path(__file__).parent.parent / 'data' / 'events.db'}"
    SITE_URL: str = "http://localhost:8090"
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    STATIC_DIR: str = str(Path(__file__).parent / "static")
    TEMPLATES_DIR: str = str(Path(__file__).parent / "templates")
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432
    DB_NAME: str = "allevents"
    DB_USER: str = "allevents"
    DB_PASSWORD: str = ""
    SCRAPER_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def base_path(self) -> str:
        path = urlparse(self.SITE_URL).path.rstrip("/")
        return path

    @property
    def database_url(self) -> str:
        if self.DB_HOST and self.DB_PASSWORD:
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        return self.DATABASE_URL


settings = Settings()
