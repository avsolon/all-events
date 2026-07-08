import logging
from sqlalchemy import select

from app.database import async_session
from app.models.category import Category

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    {"name": "Конференции", "slug": "conference", "description": "Деловые конференции, форумы, симпозиумы", "icon": "conference"},
    {"name": "Тренинги", "slug": "training", "description": "Бизнес-тренинги, семинары, мастер-классы", "icon": "training"},
    {"name": "Нетворкинг", "slug": "networking", "description": "Нетворкинг-сессии, бизнес-завтраки, встречи", "icon": "networking"},
    {"name": "Выставки", "slug": "exhibition", "description": "Деловые выставки, ярмарки, экспозиции", "icon": "exhibition"},
    {"name": "Лекции", "slug": "lecture", "description": "Лекции, открытые уроки, образовательные мероприятия", "icon": "lecture"},
    {"name": "Стартапы", "slug": "startup", "description": "Стартап-мероприятия, питч-сессии, акселераторы", "icon": "startup"},
    {"name": "Форумы", "slug": "forum", "description": "Бизнес-форумы, экономические форумы", "icon": "forum"},
    {"name": "Вебинары", "slug": "webinar", "description": "Онлайн-вебинары, онлайн-конференции", "icon": "webinar"},
    {"name": "Курсы", "slug": "courses", "description": "Курсы повышения квалификации, MBA, бизнес-образование", "icon": "courses"},
    {"name": "Бесплатные", "slug": "free", "description": "Бесплатные бизнес-мероприятия", "icon": "free"},
]


async def init_categories():
    async with async_session() as session:
        for cat_data in DEFAULT_CATEGORIES:
            result = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                category = Category(**cat_data)
                session.add(category)
        await session.commit()
        logger.info(f"Initialized {len(DEFAULT_CATEGORIES)} default categories")
