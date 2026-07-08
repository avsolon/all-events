import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HtmlScraper(BaseScraper):
    async def parse(self) -> List[Dict[str, Any]]:
        events = []
        cfg = self.source.get("parse_config", {})
        base_url = self.source["base_url"]
        endpoint = cfg.get("endpoint", "/")
        url = f"{base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=30, verify=False, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")
                items = soup.select(cfg.get("list_selector", ".event-card"))

                for item in items:
                    try:
                        event = self._parse_item(item, cfg, base_url)
                        if event and event.get("title"):
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Error parsing HTML item from {self.source['name']}: {e}")
                        continue
        except Exception as e:
            logger.error(f"HTML scraper error for {self.source['name']}: {e}")

        return events

    def _parse_item(self, item, cfg: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
        title_el = item.select_one(cfg.get("title_selector", "a"))
        title = title_el.get_text(strip=True) if title_el else ""

        if not title:
            return None

        link_el = item.select_one(cfg.get("link_selector", "a"))
        link = ""
        if link_el:
            href = link_el.get("href", "")
            link = urljoin(base_url, href) if href else ""

        date_el = item.select_one(cfg.get("date_selector", ".date"))
        date_text = date_el.get_text(strip=True) if date_el else ""
        start_date = self._parse_date(date_text)

        price_el = item.select_one(cfg.get("price_selector", ".price"))
        price_text = price_el.get_text(strip=True) if price_el else ""
        price, _, is_free = self.parse_price(price_text) if price_text else (None, "", False)

        desc_el = item.select_one(cfg.get("description_selector", ".description"))
        description = desc_el.get_text(strip=True) if desc_el else ""

        img_el = item.select_one("img")
        image_url = ""
        if img_el:
            src = img_el.get("src", "") or img_el.get("data-src", "")
            image_url = urljoin(base_url, src) if src else ""

        external_id = self.make_external_id(link or title)

        return self.normalize_event({
            "external_id": external_id,
            "title": title,
            "description": description,
            "url": link,
            "image_url": image_url,
            "start_date": start_date,
            "end_date": None,
            "city": self.city,
            "address": "",
            "venue": "",
            "price": price,
            "price_text": price_text,
            "is_free": is_free,
            "organizer": "",
            "tags": "",
        })

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        if not date_text:
            return None

        date_text = date_text.strip().lower()
        now = datetime.now()

        months_ru = {
            "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "июн": 6,
            "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
            "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
            "ноября": 11, "декабря": 12,
        }

        patterns = [
            r"(\d{1,2})\s+(\w+)\s+(\d{4})",
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
            r"(\d{1,2})\.(\d{1,2})",
            r"(\d{4})-(\d{1,2})-(\d{1,2})",
            r"(\d{1,2})\s+(\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, date_text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        if pattern.startswith(r"(\d{1,2})\s+(\w+)"):
                            day, month_str, year = int(groups[0]), groups[1].lower(), int(groups[2])
                            month = months_ru.get(month_str)
                            if month:
                                return datetime(year, month, day)
                        elif "." in pattern:
                            if pattern.count(".") == 2:
                                day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                                return datetime(year, month, day)
                            else:
                                day, month = int(groups[0]), int(groups[1])
                                year = now.year
                                return datetime(year, month, day)
                        else:
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            return datetime(year, month, day)
                    elif len(groups) == 2:
                        if pattern.startswith(r"(\d{1,2})\s+(\w+)"):
                            day, month_str = int(groups[0]), groups[1].lower()
                            month = months_ru.get(month_str)
                            if month:
                                year = now.year
                                return datetime(year, month, day)
                        else:
                            day, month = int(groups[0]), int(groups[1])
                            year = now.year
                            return datetime(year, month, day)
                except (ValueError, KeyError):
                    continue

        return None
