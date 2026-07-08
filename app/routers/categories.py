from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import EventService

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("")
async def list_categories(db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    return await service.get_categories()


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    service = EventService(db)
    return await service.get_sources()
