from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event
from app.models.category import Category


class EventService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_events(
        self,
        categories: Optional[List[int]] = None,
        is_free: Optional[bool] = None,
        is_online: Optional[bool] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        source_id: Optional[str] = None,
        sort_by: str = "start_date",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = select(Event).options(selectinload(Event.categories)).where(Event.is_active == True)

        if categories:
            query = query.where(
                Event.categories.any(Category.id.in_(categories))
            )

        if is_free is not None:
            query = query.where(Event.is_free == is_free)

        if is_online is not None:
            query = query.where(Event.is_online == is_online)

        if date_from:
            query = query.where(Event.start_date >= datetime.combine(date_from, datetime.min.time()))

        if date_to:
            query = query.where(
                or_(
                    Event.start_date <= datetime.combine(date_to, datetime.max.time()),
                    Event.end_date <= datetime.combine(date_to, datetime.max.time()),
                )
            )

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Event.title.ilike(search_filter),
                    Event.description.ilike(search_filter),
                    Event.tags.ilike(search_filter),
                    Event.organizer.ilike(search_filter),
                    Event.venue.ilike(search_filter),
                )
            )

        if source_id:
            query = query.where(Event.source_id == source_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        sort_column = getattr(Event, sort_by, Event.start_date)
        order_func = sort_column.desc() if sort_order == "desc" else sort_column.asc()
        query = query.order_by(order_func, Event.id)

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        events = result.scalars().all()

        return {
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        }

    async def get_event(self, event_id: int) -> Optional[Event]:
        query = select(Event).options(selectinload(Event.categories)).where(Event.id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_calendar_data(
        self,
        month: int,
        year: int,
        categories: Optional[List[int]] = None,
        is_free: Optional[bool] = None,
    ) -> Dict[int, List[Event]]:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        query = (
            select(Event)
            .options(selectinload(Event.categories))
            .where(
                Event.is_active == True,
                Event.start_date >= start,
                Event.start_date < end,
            )
        )

        if categories:
            query = query.where(Event.categories.any(Category.id.in_(categories)))
        if is_free is not None:
            query = query.where(Event.is_free == is_free)

        query = query.order_by(Event.start_date)

        result = await self.session.execute(query)
        events = result.scalars().all()

        calendar = {}
        for event in events:
            day = event.start_date.day
            if day not in calendar:
                calendar[day] = []
            calendar[day].append(event)

        return calendar

    async def get_categories(self) -> List[Category]:
        result = await self.session.execute(select(Category).order_by(Category.name))
        return result.scalars().all()

    async def get_sources(self) -> List[str]:
        result = await self.session.execute(
            select(Event.source_id).where(Event.is_active == True).distinct()
        )
        return result.scalars().all()

    async def get_upcoming_count(self) -> int:
        now = datetime.now()
        query = select(func.count()).where(
            Event.is_active == True,
            Event.start_date >= now,
        )
        result = await self.session.execute(query)
        return result.scalar()

    async def get_free_count(self) -> int:
        query = select(func.count()).where(
            Event.is_active == True,
            Event.is_free == True,
        )
        result = await self.session.execute(query)
        return result.scalar()
