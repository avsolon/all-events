#!/usr/bin/env python3
import asyncio
import logging
import sys

import uvicorn

from app.config import settings
from app.scrapers.manager import run_all_scrapers
from app.bot.telegram_bot import init_bot, start_polling
from app.database import init_db
from app.services.category_initializer import init_categories

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def startup():
    await init_db()
    await init_categories()


async def run_scrapers():
    logger.info("Running scraping...")
    try:
        events = await run_all_scrapers()
        logger.info(f"Scraping completed. {len(events) if events else 0} events collected.")
    except Exception as e:
        logger.error(f"Scraping error: {e}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "web"

    if mode == "scrape":
        asyncio.run(_run_scrape())
        return

    if mode == "bot":
        asyncio.run(_run_bot())
        return

    if mode == "web":
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.DEBUG,
            log_level="info",
        )
        return

    if mode == "all":
        asyncio.run(_run_all())
        return

    logger.error(f"Unknown mode: {mode}")
    sys.exit(1)


async def _run_scrape():
    await startup()
    await run_scrapers()


async def _run_bot():
    await startup()
    await init_bot()
    logger.info("Starting Telegram bot polling...")
    await start_polling()


async def _run_all():
    await startup()
    await init_bot()
    bot_task = asyncio.create_task(start_polling())
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), bot_task)


if __name__ == "__main__":
    main()
