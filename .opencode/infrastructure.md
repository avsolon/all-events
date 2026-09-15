# Infrastructure

## Stack / services
- FastAPI + SQLAlchemy async + PostgreSQL (prod) / SQLite (local dev: data/events.db). Front: Jinja2 + Tailwind, JS list/calendar.
- Scraper microservice (python, httpx) — НЕ в docker-compose, запускается вручную: `python3 -m app.main` из `scraper-microservice/` (свой .env, venv не требуется).
- Production: docker-compose services db (postgres:16-alpine), web, bot (Telegram). nginx: http://138.124.70.3/site-all-events.

## Docker / deployment
- Server IP: 138.124.70.3. SSH root → Permission denied (publickey,password) — деплой выполняет пользователь на сервере:
  `git pull && docker compose build web && docker compose up -d web`
- Deploy = только server code (app/ + docker-compose). Скрейпер локальный, деплоить не нужно.

## Env / configs
- Local scraper `.env` (gitignored): API_URL=http://138.124.70.3/site-all-events/api/events/upsert, API_KEY=my-secret-key, SCRAPE_INTERVAL_HOURS=6, TIMEPAD_API_TOKEN=e034b30c73259908340aacfa162769c0b3fd1327 (view_events; 403 без него).
- TimePad params (scraper-microservice/config/sources.json, parse_config.params): city_ids [78], limit 100, fields location,description,categories; в коде timepad.py добавляются starts_at_min/max и sort=starts_at asc.
- Server .env (на сервере): при необходимости токен TimePad не нужен — скрейпер работает локально.