from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import EventService
from app.config import settings

jinja_env = Environment(
    loader=FileSystemLoader(settings.TEMPLATES_DIR),
    auto_reload=False,
    cache_size=50,
)
templates = jinja_env
router = APIRouter(tags=["pages"])


def render(name: str, context: dict) -> str:
    template = templates.get_template(name)
    return template.render(base_path=settings.base_path, **context)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    upcoming = await service.get_events(page_size=6, sort_order="asc")
    categories = await service.get_categories()
    content = render("index.html", {
        "events": upcoming["events"],
        "categories": categories,
        "stats": {
            "total": upcoming["total"],
            "free": await service.get_free_count(),
        },
    })
    return HTMLResponse(content)


@router.get("/events", response_class=HTMLResponse)
async def events_page(request: Request, db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    categories = await service.get_categories()
    sources = await service.get_sources()
    content = render("events.html", {
        "categories": categories,
        "sources": sources,
    })
    return HTMLResponse(content)


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request, db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    categories = await service.get_categories()
    content = render("calendar.html", {"categories": categories})
    return HTMLResponse(content)


@router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(request: Request, event_id: int, db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    event = await service.get_event(event_id)
    if not event:
        return RedirectResponse(url=f"{settings.base_path}/events")
    content = render("event_detail.html", {"event": event})
    return HTMLResponse(content)
