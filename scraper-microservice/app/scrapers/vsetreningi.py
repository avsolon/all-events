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


class VsetreningiScraper(BaseScraper):
    BASE_URL = "https://vsetreningi.ru"

    async def parse(self) -> List[Dict[str, Any]]:
        seen = set()
        events = []

        for path in ["/nsk/", "/nsk/timetable/"]:
            try:
                page_events = await self._fetch_and_parse(path)
                for ev in page_events:
                    url = ev.get("url", "")
                    if url not in seen:
                        seen.add(url)
                        events.append(ev)
            except Exception as e:
                logger.warning(f"Vsetreningi: failed {path}: {e}")

        logger.info(f"{self.source_name}: {len(events)} events")
        return events

    async def _fetch_and_parse(self, path: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}{path}"
        async with self._client() as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        rows = soup.select("table.table.events tr.vevent1")
        result = []
        for row in rows:
            try:
                parsed = self._parse_row(row)
                if parsed:
                    result.append(parsed)
            except Exception as e:
                logger.debug(f"Vsetreningi: parse error: {e}")
        return result

    def _parse_row(self, row) -> Optional[Dict[str, Any]]:
        title_el = row.select_one(
            'td:last-child .trainingHeader a[href*="/trainings/"]'
        )
        if not title_el:
            return None

        title = title_el.get_text(strip=True)
        if not title:
            return None

        rel_url = title_el.get("href", "")
        full_url = urljoin(self.BASE_URL, rel_url)
        external_id = self.make_external_id(full_url)

        day_el = row.select_one("td.firstChild .dateBlock .dayNum")
        time_el = row.select_one("td.firstChild .dateBlock .gray span")
        start_date = self._parse_date_text(
            day_el.get_text(strip=True) if day_el else "",
            time_el.get_text(strip=True) if time_el else "",
        )

        price, price_text, is_free = self._extract_price(row)

        trainer_el = row.select_one(
            "td:last-child .trainers .trainer td:last-child a"
        )
        organizer_el = row.select_one(
            "td:last-child .organizers .organizer a.org"
        )
        trainer = trainer_el.get_text(strip=True) if trainer_el else ""
        organizer = organizer_el.get_text(strip=True) if organizer_el else ""

        icon = row.select_one("td:last-child .trainingHeader i.icon")
        is_online = False
        if icon:
            title_attr = icon.get("title", "")
            cls = icon.get("class", [])
            if "webinar" in cls or "вебинар" in title_attr.lower():
                is_online = True

        return self.normalize_event({
            "external_id": external_id,
            "title": title,
            "description": "",
            "url": full_url,
            "image_url": "",
            "start_date": start_date,
            "end_date": None,
            "city": self.city,
            "address": "",
            "venue": "",
            "price": price,
            "price_text": price_text,
            "is_free": is_free,
            "is_online": is_online,
            "organizer": organizer,
            "contact_phone": "",
            "contact_email": "",
            "tags": "",
        })

    def _extract_price(self, row) -> tuple:
        free_el = row.select_one("td:last-child .free-admission")
        if free_el:
            return 0, "Бесплатно", True

        payment_input = row.select_one(
            'td:last-child .eventRegBox input[name="payment"]'
        )
        if payment_input:
            val = payment_input.get("value", "0")
            try:
                amount = float(val)
                if amount > 0:
                    return amount, f"{int(amount)} руб.", False
            except ValueError:
                pass

        discount_el = row.select_one(
            "td:last-child .order_button nobr span:not(.ruble_arial):not(.applicate_img)"
        )
        if discount_el:
            text = discount_el.get_text(strip=True)
            nums = re.findall(r"[\d\s]+", text.replace(" ", ""))
            if nums:
                try:
                    amount = float(nums[0].strip())
                    return amount, text, False
                except ValueError:
                    pass
            return None, text, False

        return None, "", False

    def _parse_date_text(self, day_text: str, time_text: str) -> Optional[datetime]:
        if not day_text:
            return None

        day_text = day_text.strip().lower()
        hour, minute = 0, 0
        if time_text:
            match = re.match(r"(\d{1,2}):(\d{2})", time_text.strip())
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))

        pattern = r"(\d{1,2})\s+(\w+)"
        match = re.search(pattern, day_text)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            month = MONTHS_RU.get(month_str)
            if month:
                now = datetime.now()
                year = now.year
                if month < now.month or (month == now.month and day < now.day):
                    year += 1
                return datetime(year, month, day, hour, minute)

        return None
