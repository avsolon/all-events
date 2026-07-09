from datetime import date, datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, async_session
from app.models.event import Event
from app.models.category import Category
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


class EventUpsert(BaseModel):
    source_id: str
    external_id: str = ""
    title: str
    description: str = ""
    url: str = ""
    image_url: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    city: str = "Новосибирск"
    address: str = ""
    venue: str = ""
    price: Optional[float] = None
    price_text: str = ""
    is_free: bool = False
    is_online: bool = False
    organizer: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    tags: str = ""
    category_slugs: List[str] = Field(default_factory=list)


@router.post("/upsert")
async def upsert_events(
    events: List[EventUpsert],
    authorization: str = Header(""),
):
    if settings.SCRAPER_API_KEY and authorization != f"Bearer {settings.SCRAPER_API_KEY}":
        raise HTTPException(status_code=403, detail="Invalid API key")

    saved = 0
    async with async_session() as session:
        for ev in events:
            try:
                external_id = ev.external_id or ev.url or ev.title
                result = await session.execute(
                    select(Event).where(
                        Event.source_id == ev.source_id,
                        Event.external_id == external_id,
                    )
                )
                existing = result.scalar_one_or_none()

                data = ev.model_dump(exclude={"category_slugs"})
                data["external_id"] = external_id

                if existing:
                    for key, value in data.items():
                        if key not in ("external_id", "source_id") and value is not None:
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                    event_obj = existing
                else:
                    data.pop("external_id", None)
                    event_obj = Event(**{**data, "external_id": external_id})
                    session.add(event_obj)

                await session.flush()

                slugs = ev.category_slugs
                if not slugs and ev.tags:
                    TAG_MAP = {
                        "конференция": "conference", "тренинг": "training",
                        "семинар": "lecture", "лекция": "lecture",
                        "нетворкинг": "networking", "выставка": "exhibition",
                        "стартап": "startup", "инновации": "startup",
                        "форум": "forum", "бесплатно": "free",
                        "обучение": "courses", "предпринимательство": "startup",
                        "акселератор": "startup", "консультация": "training",
                        "бизнес": "conference",
                    }
                    slugs = list(dict.fromkeys(
                        TAG_MAP[t] for t in ev.tags.split(",") if t.strip().lower() in TAG_MAP
                    ))
                if slugs:
                    cats = await session.execute(
                        select(Category).where(Category.slug.in_(slugs))
                    )
                    event_obj.categories = cats.scalars().all()

                saved += 1
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error saving event {ev.title}: {e}")

        await session.commit()

    return {"saved": saved}


@router.get("")
async def list_events(
    categories: Optional[List[int]] = Query(None),
    is_free: Optional[bool] = Query(None),
    is_online: Optional[bool] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    sort_by: str = Query("start_date"),
    sort_order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = EventService(db)
    return await service.get_events(
        categories=categories,
        is_free=is_free,
        is_online=is_online,
        date_from=date_from,
        date_to=date_to,
        search=search,
        source_id=source,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.get("/calendar/{year}/{month}")
async def calendar_data(
    year: int,
    month: int,
    categories: Optional[List[int]] = Query(None),
    is_free: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = EventService(db)
    data = await service.get_calendar_data(month, year, categories=categories, is_free=is_free)
    result = []
    for day, events in data.items():
        result.append({
            "day": day,
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "start_date": e.start_date.isoformat(),
                    "is_free": e.is_free,
                    "source_id": e.source_id,
                }
                for e in events
            ],
        })
    return {"year": year, "month": month, "days": result}


@router.get("/stats/overview")
async def stats_overview(db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    upcoming = await service.get_upcoming_count()
    free = await service.get_free_count()
    return {"upcoming": upcoming, "free": free}



