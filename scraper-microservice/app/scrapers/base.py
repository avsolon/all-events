from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

import httpx


class BaseScraper(ABC):
    def __init__(self, source_config: Dict[str, Any]):
        self.source = source_config
        self.source_id = source_config["id"]
        self.source_name = source_config["name"]
        self.city = source_config.get("city", "Новосибирск")
        self.category_tags = source_config.get("category_tags", [])

    def _client(self) -> httpx.AsyncClient:
        kwargs = {
            "timeout": 30,
            "verify": False,
            "follow_redirects": True,
        }
        return httpx.AsyncClient(**kwargs)

    @abstractmethod
    async def parse(self) -> List[Dict[str, Any]]:
        pass

    def make_external_id(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    TAG_TO_SLUG = {
        "конференция": "conference",
        "тренинг": "training",
        "семинар": "lecture",
        "лекция": "lecture",
        "нетворкинг": "networking",
        "выставка": "exhibition",
        "стартап": "startup",
        "инновации": "startup",
        "форум": "forum",
        "бесплатно": "free",
        "обучение": "courses",
        "предпринимательство": "startup",
        "акселератор": "startup",
        "консультация": "training",
        "бизнес": "conference",
    }

    def _category_slugs(self) -> List[str]:
        seen = set()
        slugs = []
        for tag in self.category_tags:
            slug = self.TAG_TO_SLUG.get(tag.lower())
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)
        return slugs

    def normalize_event(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "external_id": raw.get("external_id", ""),
            "title": raw.get("title", "").strip(),
            "description": raw.get("description", ""),
            "url": raw.get("url", ""),
            "image_url": raw.get("image_url", ""),
            "start_date": raw.get("start_date"),
            "end_date": raw.get("end_date"),
            "city": raw.get("city", self.city),
            "address": raw.get("address", ""),
            "venue": raw.get("venue", ""),
            "price": raw.get("price"),
            "price_text": raw.get("price_text", ""),
            "is_free": raw.get("is_free", False),
            "is_online": raw.get("is_online", False),
            "organizer": raw.get("organizer", ""),
            "contact_phone": raw.get("contact_phone", ""),
            "contact_email": raw.get("contact_email", ""),
            "tags": ",".join(self.category_tags) if not raw.get("tags") else raw.get("tags", ""),
            "category_slugs": self._category_slugs(),
        }

    def parse_price(self, price_str: str) -> tuple:
        if not price_str:
            return None, "", False
        price_str = price_str.strip().lower()
        if "бесплатно" in price_str or "free" in price_str or price_str == "0":
            return 0, price_str, True
        import re
        nums = re.findall(r"[\d\s]+", price_str.replace(" ", ""))
        if nums:
            try:
                price = float(nums[0].strip())
                return price, price_str, False
            except ValueError:
                pass
        return None, price_str, False
