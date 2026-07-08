from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


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



