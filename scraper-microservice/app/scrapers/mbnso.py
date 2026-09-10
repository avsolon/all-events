import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

MONTHS_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MAX_PAGES = 15


class MbnsoScraper(BaseScraper):
    BASE_URL = "https://mbnso.ru"

    CATEGORY_PATHS = [
        "/projects/obuchenie/",
        "/projects/vystavki/",
    ]

    async def parse(self) -> List[Dict[str, Any]]:
        seen = set()
        events = []

        for path in self.CATEGORY_PATHS:
            for page in range(1, MAX_PAGES + 1):
                try:
                    page_events = await self._fetch_page(path, page)
                except Exception as e:
                    logger.warning(f"Mbnso: failed {path} page {page}: {e}")
                    break

                new_events = []
                for ev in page_events:
                    url = ev.get("url", "")
                    if url not in seen:
                        seen.add(url)
                        new_events.append(ev)

                if not new_events:
                    break

                events.extend(new_events)

        logger.info(f"{self.source_name}: {len(events)} events")
        return events

    async def _fetch_page(self, path: str, page: int) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}{path}"
        if page > 1:
            url += f"?PAGEN_1={page}"

        async with self._client() as client:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        result = []
        for card in soup.select("div.event-list__item.event-item"):
            if "event-item--completed" in card.get("class", []):
                continue
            try:
                parsed = self._parse_card(card)
                if parsed:
                    result.append(parsed)
            except Exception as e:
                logger.debug(f"Mbnso: parse error: {e}")
        return result

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        title_el = card.select_one("h3.event-item__title")
        link_el = card.select_one("a:has(h3.event-item__title)")
        if not title_el or not link_el:
            return None

        title = title_el.get_text(strip=True)
        if not title:
            return None

        rel_url = link_el.get("href", "")
        full_url = urljoin(self.BASE_URL, rel_url)
        external_id = self.make_external_id(full_url)

        spans = [
            s.get_text(strip=True)
            for s in card.select(".event-item__info span")
            if s.get_text(strip=True)
        ]
        date_text = spans[0] if spans else ""
        time_text = ""
        format_text = ""
        for span in spans[1:]:
            if re.match(r"^\d{1,2}:\d{2}$", span):
                time_text = span
            else:
                format_text = span

        start_date, end_date = self._parse_dates(date_text, time_text)

        category_el = card.select_one(".event-item__category")
        category = category_el.get_text(strip=True) if category_el else ""

        image_url = ""
        img_el = card.select_one("a.event-item__preview img")
        if img_el:
            src = img_el.get("src", "")
            image_url = urljoin(self.BASE_URL, src) if src else ""

        is_online = "онлайн" in format_text.lower()

        return self.normalize_event({
            "external_id": external_id,
            "title": title,
            "description": "",
            "url": full_url,
            "image_url": image_url,
            "start_date": start_date,
            "end_date": end_date,
            "city": self.city,
            "address": "",
            "venue": "",
            "price": 0,
            "price_text": "Бесплатно",
            "is_free": True,
            "is_online": is_online,
            "organizer": self.source_name,
            "contact_phone": "",
            "contact_email": "",
            "tags": category,
        })

    def _parse_dates(self, date_text: str, time_text: str):
        if not date_text:
            return None, None

        date_text = date_text.strip().lower()
        hour, minute = 0, 0
        if time_text:
            match = re.match(r"(\d{1,2}):(\d{2})", time_text)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))

        parts = re.split(r"\s*[—–-]\s*", date_text)
        start = self._parse_single_date(parts[0])
        if not start:
            return None, None

        start = start.replace(hour=hour, minute=minute)
        if len(parts) > 1:
            end = self._parse_single_date(parts[1])
            if end:
                if (end.month, end.day) < (start.month, start.day):
                    end = end.replace(year=end.year + 1)
                return start, end

        return start, None

    def _parse_single_date(self, text: str) -> Optional[datetime]:
        match = re.search(r"(\d{1,2})\s+(\w+)", text)
        if not match:
            return None

        day = int(match.group(1))
        month_str = match.group(2).lower()
        month = MONTHS_RU.get(month_str)
        if not month:
            return None

        now = datetime.now()
        year = now.year
        if (month, day) < (now.month, now.day):
            year += 1
        return datetime(year, month, day)