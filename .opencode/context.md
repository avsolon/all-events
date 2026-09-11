# All-Events project state

## Goal
Novosibirsk business-events aggregator. Front (Jinja2 + Tailwind, server-rendered pages + JS list/calendar) + FastAPI + SQLAlchemy async + PostgreSQL/SQLite. Scraper microservice fills events via idempotent upsert.

## Architecture
- `app/` FastAPI app; entry `python3 run.py web` (port 8000). Production: docker-compose (db, web, bot), nginx at 138.124.70.3/site-all-events.
- `scraper-microservice/` — loop every SCRAPE_INTERVAL_HOURS(6h), scrapes enabled sources from `config/sources.json`, POSTs chunks of 50 to `/api/events/upsert` with Bearer API_KEY.
- Categories resolved server-side: scraper sends `category_slugs` (source-level via `_category_slugs()`); server upsert ALSO scans title/description/tags keywords to assign categories per-event.
- Event filtering in `EventService.get_events`: `is_upcoming` = start_date >= now (предстоящие); `exclude_ended` = end_date is null OR end_date >= now (Все: ongoing + upcoming). Main page always is_upcoming=True.
- Local dev SQLite: data/events.db. `.env` SCRAPER_API_KEY empty → auth skipped locally.
- Git: remote git@github.com:avsolon/all-events.git, branch main. Committer identity auto-configured (Ayesha Cyril), pushes work despite warnings.

## Categories (DB seeded by category_initializer.py)
- conference, training, networking, exhibition, lecture, accelerator («Акселлераторы»), forum, webinar, courses, free.
- Category «Стартапы» replaced with «Акселлераторы» (slug accelerator). Initializer migrates old slug 'startup' → 'accelerator' on startup.

## Key files
- app/services/event_service.py — get_events (is_upcoming/exclude_ended filters), get_calendar_data
- app/routers/events.py — /api/events upsert (keyword→category assignment) + list
- app/routers/pages.py:28 — main page (is_upcoming=True, page_size=6)
- app/templates/events.html — list page; default period "Все" (exclude_ended=true), "Предстоящие" → is_upcoming
- app/services/category_initializer.py — DEFAULT_CATEGORIES + startup→accelerator migration
- scraper-microservice/app/scrapers/base.py — TAG_TO_SLUG (акселератор→accelerator), _category_slugs