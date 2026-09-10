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


class NovosibexpoScraper(BaseScraper):
    BASE_URL = "https://www.novosibexpo.ru"

    async def parse(self) -> List[Dict[str, Any]]:
        seen = set()
        events = []

        for year in self._list_years():
            try:
                page_events = await self._fetch_listing(year)
            except Exception as e:
                logger.warning(f"Novosibexpo: failed listing year={year}: {e}")
                continue

            new_events = []
            for ev in page_events:
                url = ev.get("url", "")
                if url not in seen:
                    seen.add(url)
                    new_events.append(ev)

            if not new_events:
                continue

            for ev in new_events:
                try:
                    await self._enrich(ev)
                except Exception as e:
                    logger.debug(f"Novosibexpo: detail fail {ev.get('url')}: {e}")

            events.extend(new_events)
            if len(events) > 200:
                break

        logger.info(f"{self.source_name}: {len(events)} events")
        return events

    def _list_years(self) -> List[Optional[int]]:
        years = []
        base = self.source.get("parse_config", {}).get("years", [])
        for y in base:
            years.append(int(y))
        for y in (datetime.now().year, datetime.now().year + 1):
            if y not in years:
                years.append(y)
        return years

    async def _fetch_listing(self, year: Optional[int]) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/calendar/events.html"
        if year:
            url += f"?d={year}"

        async with self._client() as client:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept-Language": "ru-RU,ru;q=0.9",
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        result = []
        for link_el in soup.select("a[href*='/calendar/event/']"):
            try:
                card = link_el.find_parent("div", class_="tab")
                if not card:
                    continue
                parsed = self._parse_card(card)
                if parsed:
                    result.append(parsed)
            except Exception as e:
                logger.debug(f"Novosibexpo: card parse error: {e}")

        seen = set()
        unique = []
        for ev in result:
            if ev["url"] not in seen:
                seen.add(ev["url"])
                unique.append(ev)
        return unique

    def _parse_card(self, card) -> Optional[Dict[str, Any]]:
        link_el = card.select_one("a[href*='/calendar/event/']")
        title_el = card.select_one("h2")
        if not link_el or not title_el:
            return None

        title = title_el.get_text(" ", strip=True)
        rel_url = link_el.get("href", "")
        full_url = urljoin(self.BASE_URL, rel_url)
        external_id = self.make_external_id(full_url)

        desc_el = card.select_one("p")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        h5 = card.select_one("h5")
        date_text = h5.get_text(" ", strip=True) if h5 else ""
        start_date, end_date = self._parse_dates(date_text)

        address = ""
        addr_match = re.search(r",\s*(.+)", title)
        if addr_match:
            address = addr_match.group(1).strip()
            title = title[: addr_match.start()].strip()

        return self.normalize_event({
            "external_id": external_id,
            "title": title,
            "description": description,
            "url": full_url,
            "image_url": "",
            "start_date": start_date,
            "end_date": end_date,
            "city": self.city,
            "address": address,
            "venue": "МВК «Новосибирск Экспоцентр»",
            "price": None,
            "price_text": "",
            "is_free": False,
            "is_online": False,
            "organizer": self.source_name,
            "contact_phone": "",
            "contact_email": "",
            "tags": "",
        })

    async def _enrich(self, ev: Dict[str, Any]) -> None:
        url = ev["url"]
        headers = {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9",
        }

        async with self._client() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        img_el = soup.select_one("div.event-img.fluid-img img")
        if img_el:
            src = img_el.get("src", "")
            if src:
                ev["image_url"] = urljoin(self.BASE_URL, src)

        venue_el = soup.find("em", class_="grey", string=lambda t: t and "Место" in t)
        if venue_el:
            h4 = venue_el.find_next_sibling("h4")
            if h4:
                ev["address"] = h4.get_text(" ", strip=True)

        desc_el = soup.select_one("div.content-box.float-right")
        if desc_el:
            desc = desc_el.get_text(" ", strip=True)
            if len(desc) > len(ev["description"]):
                ev["description"] = desc

        big_el = soup.find("big")
        if big_el:
            date_text = big_el.get_text(strip=True)
            start_date, end_date = self._parse_short_dates(date_text)
            if start_date:
                ev["start_date"] = start_date
            if end_date:
                ev["end_date"] = end_date

    def _parse_dates(self, date_text: str):
        if not date_text:
            return None, None
        date_text = date_text.strip().lower()
        parts = re.split(r"\s*[—–-]\s*", date_text)
        start = self._parse_single_date(parts[0])
        if not start:
            return None, None
        if len(parts) > 1:
            end = self._parse_single_date(parts[1])
            if end:
                if (end.month, end.day) < (start.month, start.day):
                    end = end.replace(year=end.year + 1)
                return start, end
        return start, None

    def _parse_short_dates(self, date_text: str):
        if not date_text:
            return None, None
        parts = re.split(r"\s*[—–-]\s*", date_text.strip())
        start = self._parse_short_date(parts[0])
        if not start:
            return None, None
        if len(parts) > 1:
            end = self._parse_short_date(parts[1], hint_year=start.year)
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

    def _parse_short_date(self, text: str, hint_year: Optional[int] = None) -> Optional[datetime]:
        match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
        if not match:
            return None
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))
        if year < 100:
            year += 2000
        if hint_year and year < hint_year:
            year = hint_year
        return datetime(year, month, day)