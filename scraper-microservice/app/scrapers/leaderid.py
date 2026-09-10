import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

API_SEARCH = "/api/v4/events/search"


def _extract_description(full_info) -> str:
    if not full_info:
        return ""
    if isinstance(full_info, dict):
        blocks = full_info.get("blocks", [])
    else:
        try:
            blocks = json.loads(full_info).get("blocks", [])
        except (ValueError, AttributeError):
            return str(full_info)
    parts = []
    for block in blocks:
        if block.get("type") != "paragraph":
            continue
        text = (block.get("data") or {}).get("text", "")
        if text:
            parts.append(re.sub(r"<[^>]+>", "", text).strip())
    return "\n".join(p for p in parts if p)


def _parse_dt(value: str, tz_minutes: int) -> datetime:
    if not value:
        return None
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone(timedelta(minutes=tz_minutes)))


class LeaderIdScraper(BaseScraper):
    async def parse(self) -> List[Dict[str, Any]]:
        events = []
        cfg = self.source.get("parse_config", {})
        base_url = self.source["base_url"].rstrip("/")
        endpoint = cfg.get("endpoint", API_SEARCH)
        city_id = cfg.get("city_id", 892)
        page_size = cfg.get("page_size", 50)
        max_pages = cfg.get("max_pages", 3)

        url = f"{base_url}{endpoint}"

        try:
            async with self._client() as client:
                for page in range(1, max_pages + 1):
                    params = {
                        "cityId": city_id,
                        "actual": 1,
                        "sort": "date",
                        "paginationSize": page_size,
                        "paginationPage": page,
                        "expand": "photo, themes, type, place",
                    }
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json().get("data", {})
                    items = data.get("_items", [])

                    for item in items:
                        try:
                            event = self._parse_item(item)
                            if event:
                                events.append(event)
                        except Exception as e:
                            logger.warning(f"Error parsing leader-id item {item.get('id')}: {e}")

                    page_count = (data.get("_meta") or {}).get("pageCount", 1)
                    if page >= page_count or not items:
                        break
        except Exception as e:
            logger.error(f"Leader-ID API error: {e}")

        return events

    def _parse_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if item.get("status") != "published" or item.get("finished"):
            return None

        event_id = item.get("id")
        url = f"{self.source['base_url'].rstrip('/')}/events/{event_id}"
        external_id = self.make_external_id(url)

        tz_minutes = (item.get("timezone") or {}).get("minutes") or 420
        start_date = _parse_dt(item.get("date_start"), tz_minutes)
        end_date = _parse_dt(item.get("date_end"), tz_minutes)

        place = item.get("place") or {}
        space = item.get("space") or {}
        address = place.get("address") or {}
        venue = space.get("name") or place.get("name") or ""
        street_parts = [address.get("street"), address.get("house")]
        addr = ", ".join(p for p in street_parts if p)

        event_type = (item.get("type") or {}).get("name", "")
        themes = [(t.get("name") or "") for t in (item.get("themes") or []) if isinstance(t, dict)]
        tags = [t for t in [event_type] + themes if t]

        return self.normalize_event({
            "external_id": external_id,
            "title": item.get("full_name", ""),
            "description": _extract_description(item.get("full_info")),
            "url": url,
            "image_url": item.get("photo", ""),
            "start_date": start_date,
            "end_date": end_date,
            "city": item.get("city") or self.city,
            "address": addr,
            "venue": venue,
            "is_online": item.get("format") == "online",
            "organizer": (item.get("organization") or {}).get("name", "") if item.get("organization") else "",
            "tags": ", ".join(tags),
        })