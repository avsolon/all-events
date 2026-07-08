import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import init_db
from app.routers import events, categories, pages
from app.scrapers.manager import run_all_scrapers
from app.services.category_initializer import init_categories

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scrape_all():
    logger.info("Running scheduled scraping...")
    try:
        events = await run_all_scrapers()
        logger.info(f"Scraping completed: {len(events) if events else 0} events.")
    except Exception as e:
        logger.error(f"Scraping error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting All Events application...")
    await init_db()
    await init_categories()
    logger.info("Database initialized with categories")

    scheduler.add_job(
        scrape_all,
        "interval",
        hours=settings.SCRAPE_INTERVAL_HOURS,
        id="scrape_events",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started: scraping every {settings.SCRAPE_INTERVAL_HOURS} hours")

    asyncio.create_task(scrape_all())

    yield
    logger.info("Shutting down All Events application...")
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

app.include_router(pages.router)
app.include_router(events.router)
app.include_router(categories.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "city": "Новосибирск"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
