#!/usr/bin/env python3
import asyncio
import logging
import sys

import uvicorn

from app.config import settings
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


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "web"

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

    logger.error(f"Unknown mode: {mode}")
    sys.exit(1)


async def _run_bot():
    await startup()
    await init_bot()
    logger.info("Starting Telegram bot polling...")
    await start_polling()


if __name__ == "__main__":
    main()
