import logging
from datetime import datetime
from typing import List, Dict, Any

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class TimePadScraper(BaseScraper):
    async def parse(self) -> List[Dict[str, Any]]:
        events = []
        cfg = self.source.get("parse_config", {})
        base_url = self.source["base_url"]
        endpoint = cfg.get("endpoint", "/events")
        params = cfg.get("params", {})

        url = f"{base_url}{endpoint}"

        try:
            async with self._client() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get("values", []):
                    try:
                        event = self._parse_item(item)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Error parsing TimePad item: {e}")
        except Exception as e:
            logger.error(f"TimePad API error: {e}")

        return events

    def _parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        starts_at = item.get("starts_at")
        ends_at = item.get("ends_at")

        start_date = None
        if starts_at:
            start_date = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))

        end_date = None
        if ends_at:
            end_date = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))

        location = item.get("location", {}) or {}
        price_info = item.get("tickets_info", {}) or {}
        is_free = price_info.get("is_free", False) if price_info else False

        tickets_min = price_info.get("price_min")
        price = None
        if tickets_min is not None:
            price = float(tickets_min) / 100 if tickets_min > 100 else float(tickets_min)
        elif is_free:
            price = 0

        url = item.get("url", "")
        external_id = self.make_external_id(url)

        tags = []
        for cat in item.get("categories", []):
            if isinstance(cat, dict):
                tags.append(cat.get("name", ""))
        if item.get("tags"):
            if isinstance(item["tags"], list):
                tags.extend(item["tags"])
            elif isinstance(item["tags"], str):
                tags.append(item["tags"])

        return self.normalize_event({
            "external_id": external_id,
            "title": item.get("name", ""),
            "description": item.get("description_short") or item.get("description", ""),
            "url": url,
            "image_url": item.get("poster_image", {}).get("url") if item.get("poster_image") else "",
            "start_date": start_date,
            "end_date": end_date,
            "city": self.city,
            "address": location.get("address", ""),
            "venue": location.get("name", ""),
            "price": price,
            "price_text": f"от {price} ₽" if price else "",
            "is_free": is_free,
            "is_online": item.get("type") == "online",
            "organizer": item.get("organization", {}).get("name", "") if item.get("organization") else "",
            "tags": ", ".join(tags),
        })
