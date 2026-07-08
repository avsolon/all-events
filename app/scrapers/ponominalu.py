import logging
from datetime import datetime
from typing import List, Dict, Any

import httpx

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class PonominaluScraper(BaseScraper):
    async def parse(self) -> List[Dict[str, Any]]:
        events = []
        cfg = self.source.get("parse_config", {})
        base_url = self.source["base_url"]
        endpoint = cfg.get("endpoint", "/events")
        params = cfg.get("params", {})

        url = f"{base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get("result", []) or data.get("items", []) or []
                for item in items:
                    try:
                        event = self._parse_item(item)
                        if event:
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Error parsing Ponominalu item: {e}")
        except Exception as e:
            logger.error(f"Ponominalu API error: {e}")

        return events

    def _parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        starts_at = item.get("event_start")
        ends_at = item.get("event_end")

        start_date = None
        if starts_at:
            try:
                start_date = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        end_date = None
        if ends_at:
            try:
                end_date = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        price_min = item.get("price_min")
        price = None
        is_free = item.get("is_free", False)
        if is_free:
            price = 0
        elif price_min:
            try:
                price = float(price_min)
            except (ValueError, TypeError):
                pass

        url = item.get("link") or item.get("url", "")
        external_id = self.make_external_id(url) if url else str(item.get("id", ""))

        return self.normalize_event({
            "external_id": external_id,
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "url": url,
            "image_url": item.get("poster", ""),
            "start_date": start_date,
            "end_date": end_date,
            "address": item.get("place", {}).get("address") if item.get("place") else "",
            "venue": item.get("place", {}).get("title") if item.get("place") else "",
            "city": self.city,
            "price": price,
            "price_text": f"{price} ₽" if price and not is_free else "Бесплатно" if is_free else "",
            "is_free": is_free,
            "organizer": item.get("organizer", {}).get("title") if item.get("organizer") else "",
            "tags": "",
        })
