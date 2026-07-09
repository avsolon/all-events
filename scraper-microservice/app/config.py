import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    API_URL: str = "http://localhost:8000/api/events/upsert"
    API_KEY: str = ""
    SCRAPE_INTERVAL_HOURS: int = 6
    SOURCES_PATH: str = str(Path(__file__).parent.parent / "config" / "sources.json")
    PROXY_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def sources(self) -> List[Dict[str, Any]]:
        with open(self.SOURCES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [s for s in data["sources"] if s.get("enabled", True)]


settings = Settings()
