import logging
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.event import Event
from app.models.category import Category
from app.scrapers.timepad import TimePadScraper
from app.scrapers.ponominalu import PonominaluScraper
from app.scrapers.html_scraper import HtmlScraper

logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "api": {
        "timepad": TimePadScraper,
        "ponominalu": PonominaluScraper,
    },
}


def get_scraper(source: Dict[str, Any]):
    source_type = source.get("type", "html")
    source_id = source["id"]

    if source_type == "api":
        scraper_class = SCRAPER_MAP.get(source_type, {}).get(source_id)
        if scraper_class:
            return scraper_class(source)
    return HtmlScraper(source)


async def run_all_scrapers():
    logger.info("Starting scraping all sources...")
    all_events = []

    for source in settings.sources:
        try:
            scraper = get_scraper(source)
            if scraper:
                events = await scraper.parse()
                all_events.extend(events)
                logger.info(f"Parsed {len(events)} events from {source['name']}")
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {e}")

    logger.info(f"Total events parsed: {len(all_events)}")
    await save_events(all_events)
    return all_events


async def save_events(events_data: List[Dict[str, Any]]):
    async with async_session() as session:
        for event_data in events_data:
            try:
                result = await session.execute(
                    select(Event).where(
                        Event.source_id == event_data["source_id"],
                        Event.external_id == event_data["external_id"],
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    for key, value in event_data.items():
                        if key not in ("external_id", "source_id") and value is not None:
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    event = Event(**event_data)
                    session.add(event)
            except Exception as e:
                logger.error(f"Error saving event {event_data.get('title')}: {e}")

        await session.commit()
