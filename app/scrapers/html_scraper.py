import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

FALLBACK_SELECTORS = [
    "article.event-card",
    ".event-card",
    ".event-item",
    ".news-item",
    ".news-card",
    ".afisha-item",
    ".post-item",
    ".catalog-item",
    ".main-news-card",
    ".item",
    ".card",
    "article",
    "li.event",
    "tr.event",
    "table.event tr",
]


class HtmlScraper(BaseScraper):
    async def parse(self) -> List[Dict[str, Any]]:
        events = []
        cfg = self.source.get("parse_config", {})
        base_url = self.source["base_url"]
        endpoint = cfg.get("endpoint", "/")
        params = cfg.get("params", {})

        if params:
            from urllib.parse import urlencode
            query = urlencode(params)
            url = f"{base_url}{endpoint}?{query}"
        else:
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

                items = self._find_items(soup, cfg)
                logger.info(f"{self.source['name']}: found {len(items)} items on page")

                for item in items:
                    try:
                        event = self._parse_item(item, cfg, base_url)
                        if event and event.get("title"):
                            events.append(event)
                    except Exception as e:
                        logger.warning(f"Error parsing item from {self.source['name']}: {e}")
                        continue
        except Exception as e:
            logger.error(f"HTML scraper error for {self.source['name']}: {e}")

        return events

    def _find_items(self, soup: BeautifulSoup, cfg: Dict[str, Any]) -> List[Tag]:
        configured = cfg.get("list_selector", "").strip()
        if configured:
            items = soup.select(configured)
            if items:
                return items

        for selector in FALLBACK_SELECTORS:
            items = soup.select(selector)
            if items:
                return items

        headings = soup.find_all(["h2", "h3", "h4"], limit=30)
        for h in headings:
            link = h.find("a")
            if link and link.get("href"):
                parent = h.parent
                if parent:
                    return [parent]

        return []

    def _parse_item(self, item: Tag, cfg: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
        title, link = self._extract_title_and_link(item, cfg, base_url)

        if not title:
            return None

        date_text = self._extract_text(item, cfg.get("date_selector", ".date, .time, time"))
        start_date = self._parse_date(date_text)

        price_text = self._extract_text(item, cfg.get("price_selector", ".price, .cost"))
        price, _, is_free = self.parse_price(price_text) if price_text else (None, "", False)

        description = self._extract_text(item, cfg.get("description_selector", ".desc, .text, p"))

        img_el = item.select_one("img")
        image_url = ""
        if img_el:
            src = img_el.get("src", "") or img_el.get("data-src", "")
            image_url = urljoin(base_url, src) if src else ""

        venue = self._extract_text(item, ".venue, .place, .location, .address")

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
            "address": venue,
            "venue": venue,
            "price": price,
            "price_text": price_text,
            "is_free": is_free,
            "organizer": "",
            "tags": "",
        })

    def _extract_title_and_link(self, item: Tag, cfg: Dict[str, Any], base_url: str):
        title_sel = cfg.get("title_selector", "a, h2 a, h3 a, h4 a")
        link_sel = cfg.get("link_selector", "a[href]")

        title_el = item.select_one(title_sel) if title_sel else None

        if not title_el:
            title_el = item.select_one("a, h2, h3, h4")
        title = title_el.get_text(strip=True) if title_el else ""

        if not title:
            title_el = item.find(["h2", "h3", "h4"])
            title = title_el.get_text(strip=True) if title_el else ""

        link = ""
        link_el = item.select_one(link_sel) if link_sel else None
        if not link_el:
            link_el = item.find("a", href=True)
        if link_el:
            href = link_el.get("href", "")
            if href and not href.startswith("#") and not href.startswith("javascript"):
                link = urljoin(base_url, href)

        return title, link

    def _extract_text(self, item: Tag, selector: str) -> str:
        if not selector:
            return ""
        el = item.select_one(selector)
        return el.get_text(strip=True) if el else ""

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
                        if re.match(r"^\d", pattern) and re.match(r"\w+", groups[1]):
                            day, month_str, year = int(groups[0]), groups[1].lower(), int(groups[2])
                            month = months_ru.get(month_str)
                            if month:
                                return datetime(year, month, day)
                        elif "." in pattern:
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            return datetime(year, month, day)
                        else:
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                            return datetime(year, month, day)
                    elif len(groups) == 2:
                        if re.match(r"^\d", pattern):
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
