# Open tasks

## Done (verified local / pushed)
- [x] Main page: only start_date >= now (is_upcoming start-based) — verified: 6 events, all future
- [x] List page: default "Все" = exclude_ended (279 events), "Предстоящие" = is_upcoming (215)
- [x] Ended events (e.g. Ювелирная Сибирь-2026) excluded from both filters
- [x] Category «Акселлераторы» (slug accelerator) assigned per-event via keyword scan; test events verified + cleaned
- [x] Local DB migrated (id 6 startup→accelerator, 107 events)
- [x] Commit pushed: filters + category rename
- [x] TimePad source: token in scraper .env, date-window params (starts_at_min/max, sort starts_at asc), relevance filter via category_tags, junk excluded (запись/2050-2030 fake dates/test). Commit pushed.
- [x] Full scraper pass → prod: 272 events saved (TimePad 14, ВТ 80, МБ 29, LID 109, Экспо 40) — but prod ran OLD code (no category reassignment yet)

## Blocked / next
- [ ] SERVER DEPLOY (no SSH — user must run on server): `git pull && docker compose build web && docker compose up -d web`
- [ ] After deploy: run scraper once locally (python3 -m app.main) so prod reassigns categories (акселератор) per-event
- [ ] Verify on prod: main page + /events — no old Feb events as предстоящие; Акселлераторы category populated
- [ ] (Optional) Paginate TimePad beyond 100 events if needed later

## Notes
- Production DB: old 'startup' category renamed to 'accelerator' by initializer migration on web restart; events with old assignments keep category until re-parsed.
- TimePad junk in raw API: 69 of 100 events are recordings with 2050-01-01 placeholder dates — filters handle this.
- Deploy = server code only (app/); scraper runs locally with token already in its .env.