import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any

import httpx

from app.config import settings
from app.scrapers.base import BaseScraper
from app.scrapers.html_scraper import HtmlScraper
from app.scrapers.timepad import TimePadScraper
from app.scrapers.ponominalu import PonominaluScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "api": {
        "timepad": TimePadScraper,
        "ponominalu": PonominaluScraper,
    },
}


def get_scraper(source: Dict[str, Any]) -> BaseScraper:
    source_type = source.get("type", "html")
    source_id = source["id"]
    if source_type == "api":
        scraper_class = SCRAPER_MAP.get(source_type, {}).get(source_id)
        if scraper_class:
            return scraper_class(source)
    return HtmlScraper(source)


def serialize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in event.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


async def scrape_and_send():
    headers = {"Content-Type": "application/json"}
    if settings.API_KEY:
        headers["Authorization"] = f"Bearer {settings.API_KEY}"

    all_events = []
    for source in settings.sources:
        try:
            scraper = get_scraper(source)
            events = await scraper.parse()
            logger.info(f"Parsed {len(events)} events from {source['name']}")
            all_events.extend(events)
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")

    if not all_events:
        logger.info("No events to send")
        return

    serialized = [serialize_event(e) for e in all_events]
    logger.info(f"Sending {len(serialized)} events to {settings.API_URL}")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(settings.API_URL, json=serialized, headers=headers)
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Success: {result}")
        else:
            logger.error(f"API error {response.status_code}: {response.text[:500]}")


async def run_loop():
    logger.info(f"Starting scraper microservice")
    logger.info(f"Target API: {settings.API_URL}")
    logger.info(f"Interval: {settings.SCRAPE_INTERVAL_HOURS}h")
    logger.info(f"Sources enabled: {len(settings.sources)}")

    while True:
        logger.info("Scraping cycle started")
        try:
            await scrape_and_send()
        except Exception as e:
            logger.error(f"Scraping cycle error: {e}")

        logger.info(f"Sleeping for {settings.SCRAPE_INTERVAL_HOURS} hours")
        await asyncio.sleep(settings.SCRAPE_INTERVAL_HOURS * 3600)


def main():
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
