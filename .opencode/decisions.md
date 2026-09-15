# Decisions

## 2026-09-15
- **«Предстоящие» = is_upcoming**: `start_date >= now` (не exclude_ended). Главная всегда is_upcoming → не показывает старые февральские события.
- **«Все» = exclude_ended**: `end_date IS NULL OR end_date >= now` — долгие события (напр. Catalyst.PRO до 2026-09-26) остаются в «Все» до конца.
- **Категория «Стартапы» → «Акселлераторы»** (slug accelerator): миграция startup→accelerator в category_initializer.py + keyword-скан (акселератор/акселерационн) в server upsert. Скрейпер также маппит tags (base.py TAG_TO_SLUG).
- **TimePad**:
  - Токен (view_events) обязателен: API без токена → 403. Передача — заголовок `Authorization: Bearer`, значение в scraper `.env` (gitignored), не коммитить.
  - Фильтр по дате на стороне API: `starts_at_min=today`, `starts_at_max=+1y`, `sort=starts_at` asc — иначе первые 100 результатов — сплошной мусор (записи лекций с плейсхолдер-датами 2050/2030/2045).
  - Релевантность — по `category_tags` из sources.json (бизнес/тренинг и т.п.) против name+categories/tags.
  - Дополнительно отсеиваются: «запись» в названии, год старта >= 2049 или > now+2 (фейковые даты), названия test/тест.
  - Пагинация пока не нужна (limit=100; после фильтров ~14 событий).

## 2026-09-11 (ранее)
- Скрейпер — отдельный микросервис (не в docker-compose), шлёт чанки по 50 в `/api/events/upsert`.