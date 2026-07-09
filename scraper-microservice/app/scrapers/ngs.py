import logging
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

MONTHS_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

BUSINESS_KEYWORDS_TITLE: Set[str] = {
    "бизнес", "бизнес-", "деловой", "деловая", "деловое", "деловые",
    "предпринимател", "предпринимательство",
    "стартап", "startup",
    "тренинг", "тренинги",
    "семинар",
    "конференци",
    "форум",
    "нетворкинг", "networking",
    "мастер-класс", "мастер класс", "мастеркласс",
    "воркшоп", "workshop",
    "лекци",
    "психологи",
    "продаж",
    "маркетинг",
    "менеджмент",
    "управлени",
    "инвестици",
    "финанс",
    "бухгалтер",
    "юридическ", "юрист",
    "hr", "рекрутинг",
    "коучинг", "coaching",
    "карьер",
    "образовани",
    "обучени",
    "digital",
    "e-commerce",
    "agile", "scrum",
    "b2b", "b2c", "pr",
    "seo", "smm",
    "startup", "entrepreneur",
    "sales",
    "team building", "тимбилдинг",
    "тайм-менеджмент",
    "лидерств",
    "командообразование",
    "саммит", "summit",
    "митап", "meetup",
    "акселератор", "инкубатор",
    "питч", "pitch",
    "переговор",
    "профориентаци",
    "деловой завтрак", "бизнес-завтрак", "бизнес-ланч",
    "конгресс",
    "маркетплейс",
    "франчайз", "франшиз",
    "инвестицион",
    "криптовалют",
    "блокчейн", "blockchain",
    "искусственный интеллект", "ai", "нейросет",
    "skill", "скилл",
    "soft skills", "hard skills",
}

BUSINESS_KEYWORDS_DESC: Set[str] = {
    "бизнес-тренинг", "бизнес-семинар", "бизнес-курс",
    "деловая встреча", "деловая игра",
    "повышение квалификации",
    "профессиональный тренинг",
    "открыть свое дело",
    "как открыть бизнес",
    "как начать бизнес",
    "как стать предпринимателем",
    "как заработать",
    "начало бизнеса",
    "развитие бизнеса",
    "масштабирование бизнеса",
    "курс по маркетингу",
    "курс по продажам",
    "обучение продажам",
    "обучение маркетингу",
    "обучение управлению",
    "школа бизнеса",
    "бизнес-интенсив",
    "бизнес-практикум",
    "курс предпринимателя",
    "курс для предпринимателей",
}

BUSINESS_GENRES: Set[str] = {
    "бизнес", "деловые мероприятия", "образование", "обучение",
    "лекция", "тренинг", "семинар", "конференция",
    "выставка", "форум", "нетворкинг",
    "психология", "карьера", "маркетинг",
}


class NgsScraper(BaseScraper):
    BASE_URL = "https://ngs.ru"

    EXCLUDE_CATEGORIES = re.compile(r"/afisha/(cinema|theatre|concert|kids|sport)/")

    async def parse(self) -> List[Dict[str, Any]]:
        seen: Set[str] = set()
        events: List[Dict[str, Any]] = []

        paths = ["/afisha/", "/afisha/all-events/"]
        for page in range(1, 6):
            paths.append(f"/afisha/all-events/?page={page}")
        paths.extend(["/afisha/art/", "/afisha/other/"])

        for path in paths:
            try:
                page_events = await self._fetch_and_parse(path)
                for ev in page_events:
                    url = ev.get("url", "")
                    if url not in seen:
                        seen.add(url)
                        events.append(ev)
            except Exception as e:
                logger.debug(f"NGS: failed {path}: {e}")

        logger.info(f"{self.source_name}: {len(events)} business events")
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

        html = response.text
        match = re.search(
            r'window\.initialState\s*=\s*({.*?})\s*;\s*</script>',
            html,
            re.DOTALL,
        )
        if not match:
            return []

        data = json.loads(match.group(1))
        raw_events = self._collect_events(data)
        result = []
        for raw in raw_events:
            if not self._is_business_event(raw):
                continue
            parsed = self._parse_event(raw)
            if parsed and parsed.get("start_date"):
                result.append(parsed)
        return result

    def _collect_events(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        events = []

        for section_key in ("afishaMainPage", "afishaEventsPage"):
            page = data.get(section_key)
            if not page:
                continue

            for key in ("recommended",):
                items = page.get(key, [])
                if isinstance(items, list):
                    events.extend(items)

            for key in ("todayCinema", "upcomingEvents", "freeEvents"):
                section = page.get(key, {})
                items = section.get("events", [])
                if isinstance(items, list):
                    events.extend(items)

            paginated = page.get("eventsPaginatedBlock", {})
            items = paginated.get("events", [])
            if isinstance(items, list):
                events.extend(items)

        return events

    def _is_business_event(self, raw: Dict[str, Any]) -> bool:
        title = raw.get("title", "").lower()
        description = raw.get("description", "").lower()
        genres = [g.lower() for g in raw.get("genres", [])]
        url = raw.get("url", "")

        if self.EXCLUDE_CATEGORIES.search(url):
            if not any(kw in title for kw in BUSINESS_KEYWORDS_TITLE):
                if not any(g in BUSINESS_GENRES for g in genres):
                    return False

        if any(kw in title for kw in BUSINESS_KEYWORDS_TITLE):
            return True

        if any(g in BUSINESS_GENRES for g in genres):
            return True

        if any(kw in description for kw in BUSINESS_KEYWORDS_DESC):
            return True

        return False

    def _parse_event(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        title = raw.get("title", "").strip()
        rel_url = raw.get("url", "")
        full_url = urljoin(self.BASE_URL, rel_url)

        external_id = self.make_external_id(full_url)

        image_url = ""
        img = raw.get("image", {})
        if isinstance(img, dict):
            image_url = img.get("src", "")

        start_date = self._parse_date(raw.get("startedAt", ""))

        place = raw.get("place", {})
        venue = ""
        if isinstance(place, dict):
            venue = place.get("text", "")

        description = raw.get("description", "")
        genres = raw.get("genres", [])
        tags = ", ".join(genres) if genres else ", ".join(self.category_tags)

        return self.normalize_event({
            "external_id": external_id,
            "title": title,
            "description": description,
            "url": full_url,
            "image_url": image_url,
            "start_date": start_date,
            "end_date": None,
            "city": self.city,
            "address": venue,
            "venue": venue,
            "price": None,
            "price_text": "",
            "is_free": False,
            "is_online": False,
            "organizer": "",
            "tags": tags,
        })

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        pattern = r"(\d{1,2})\s+(\w+)\s*[,]?\s*(\d{1,2}):(\d{2})"
        match = re.search(pattern, date_str)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            hour = int(match.group(3))
            minute = int(match.group(4))
            month = MONTHS_RU.get(month_str)
            if month:
                now = datetime.now()
                year = now.year
                if month > now.month:
                    year -= 1
                return datetime(year, month, day, hour, minute)

        pattern = r"(\d{1,2})\s+(\w+)"
        match = re.search(pattern, date_str)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            month = MONTHS_RU.get(month_str)
            if month:
                now = datetime.now()
                year = now.year
                if month > now.month:
                    year -= 1
                return datetime(year, month, day)

        return None
