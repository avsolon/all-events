import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.config import settings
from app.database import async_session
from app.models.event import Event
from app.services.event_service import EventService

logger = logging.getLogger(__name__)

bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


async def init_bot():
    global bot, dp
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, bot disabled")
        return

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "👋 <b>All Events Novosibirsk</b>\n\n"
            "Бот для поиска бизнес-мероприятий в Новосибирске.\n\n"
            "<b>Команды:</b>\n"
            "/start — Показать это сообщение\n"
            "/today — Мероприятия на сегодня\n"
            "/week — Мероприятия на неделю\n"
            "/upcoming — Ближайшие мероприятия\n"
            "/free — Бесплатные мероприятия\n"
            "/search <запрос> — Поиск по мероприятиям\n"
            "/categories — Категории мероприятий\n"
            "/help — Помощь",
            parse_mode="HTML",
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        await message.answer(
            "📖 <b>Помощь</b>\n\n"
            "Бот собирает бизнес-мероприятия со следующих площадок:\n"
            "• TimePad\n"
            "• Ponominalu\n"
            "• Афиша НГС\n"
            "• Expomap\n"
            "• 2do2go\n"
            "• AllConferences\n"
            "• Мой Бизнес НСО\n"
            "• ТПП НСО\n"
            "• Академпарк\n"
            "• Сибярмарка\n"
            "• ForumSib\n"
            "• НГТУ\n\n"
            "Данные обновляются каждые 6 часов.",
            parse_mode="HTML",
        )

    @dp.message(Command("today"))
    async def cmd_today(message: types.Message):
        await send_events_by_period(message, "today", "📅 <b>Мероприятия на сегодня:</b>")

    @dp.message(Command("week"))
    async def cmd_week(message: types.Message):
        await send_events_by_period(message, "week", "📅 <b>Мероприятия на неделю:</b>")

    @dp.message(Command("upcoming"))
    async def cmd_upcoming(message: types.Message):
        await send_events_by_period(message, "upcoming", "📅 <b>Ближайшие мероприятия:</b>")

    @dp.message(Command("free"))
    async def cmd_free(message: types.Message):
        async with async_session() as session:
            service = EventService(session)
            result = await service.get_events(is_free=True, page_size=10)
            await send_events_result(message, result, "🆓 <b>Бесплатные мероприятия:</b>")

    @dp.message(Command("categories"))
    async def cmd_categories(message: types.Message):
        async with async_session() as session:
            service = EventService(session)
            categories = await service.get_categories()
            lines = ["📂 <b>Категории мероприятий:</b>\n"]
            for cat in categories:
                lines.append(f"• {cat.name}")
            await message.answer("\n".join(lines), parse_mode="HTML")

    @dp.message(Command("search"))
    async def cmd_search(message: types.Message):
        query = message.text.replace("/search", "", 1).strip()
        if not query:
            await message.answer("🔍 Укажите поисковый запрос, например: /search тренинг")
            return
        async with async_session() as session:
            service = EventService(session)
            result = await service.get_events(search=query, page_size=10)
            await send_events_result(message, result, f"🔍 <b>Результаты поиска по запросу «{query}»:</b>")

    logger.info("Telegram bot initialized")
    return bot, dp


async def send_events_by_period(message: types.Message, period: str, header: str):
    async with async_session() as session:
        service = EventService(session)
        now = datetime.now()

        filters = {}
        if period == "today":
            filters["date_from"] = now.date()
            filters["date_to"] = now.date()
        elif period == "week":
            from datetime import timedelta
            filters["date_from"] = now.date()
            filters["date_to"] = (now + timedelta(days=7)).date()
        elif period == "upcoming":
            filters["date_from"] = now.date()

        result = await service.get_events(**filters, page_size=10)
        await send_events_result(message, result, header)


async def send_events_result(message: types.Message, result: dict, header: str):
    events = result.get("events", [])
    if not events:
        await message.answer(f"{header}\n\nМероприятий не найдено.")
        return

    for event in events[:5]:
        price_text = "🆓 Бесплатно" if event.is_free else (f"💰 {event.price_text or f'{event.price} ₽'}" if event.price else "")
        date_str = event.start_date.strftime("%d.%m.%Y %H:%M") if event.start_date else "Дата уточняется"

        text = (
            f"<b>{event.title}</b>\n"
            f"📅 {date_str}\n"
            f"🏢 {event.source_id}\n"
        )
        if event.venue:
            text += f"📍 {event.venue}\n"
        if price_text:
            text += f"{price_text}\n"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подробнее", url=f"{settings.SITE_URL}/events/{event.id}")],
            ]
        )

        try:
            if event.image_url:
                await message.answer_photo(
                    photo=event.image_url,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                )
            else:
                await message.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await message.answer(text, parse_mode="HTML", reply_markup=kb)

    total = result.get("total", 0)
    if total > 5:
        await message.answer(
            f"📊 Всего найдено: {total}. "
            f"Больше на сайте: {settings.SITE_URL}/events"
        )


async def start_polling():
    if not bot or not dp:
        logger.warning("Bot not initialized, skipping polling")
        return
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot)


async def notify_subscribers(event_id: int):
    if not bot:
        return
    async with async_session() as session:
        service = EventService(session)
        event = await service.get_event(event_id)
        if not event:
            return

        text = (
            f"🎉 <b>Новое мероприятие!</b>\n\n"
            f"<b>{event.title}</b>\n"
            f"📅 {event.start_date.strftime('%d.%m.%Y %H:%M') if event.start_date else ''}\n"
            f"{'🆓 Бесплатно' if event.is_free else ''}\n\n"
            f"Подробнее: {settings.SITE_URL}/events/{event.id}"
        )

        if settings.TELEGRAM_CHAT_ID:
            try:
                await bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=text, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
