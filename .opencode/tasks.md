# Open tasks

## Active / verified (local)
- [x] Main page: only start_date >= now (is_upcoming start-based) — verified: 6 events, all future
- [x] List page: default "Все" = exclude_ended (279 events), "Предстоящие" = is_upcoming (215)
- [x] Ended events (e.g. Ювелирная Сибирь-2026) excluded from both filters
- [x] Category «Акселлераторы» (slug accelerator) assigned per-event via keyword scan (title/desc/tags: акселератор/акселерационн); test events verified + cleaned
- [ ] Local DB category migrated (id 6 startup→accelerator, 107 events keep it; re-parse will reassign correctly)
- [ ] Push commit, then server: git pull && docker compose build web && docker compose up -d web
- [ ] After deploy: run scraper once (python -m app.main) so production re-assigns categories per-event
- [ ] Verify on production main page + /events that old Feb events no longer show as предстоящие

## Notes
- Production DB: old 'startup' category renamed to 'accelerator' by initializer migration on web restart; events with old assignments keep category until re-parsed.
- Deploy reminder: app/routers/events.py etc. are server code — must git pull + rebuild web container.