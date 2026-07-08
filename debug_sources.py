#!/usr/bin/env python3
"""Диагностика источников — показывает что реально возвращает каждый сайт."""
import asyncio
import json
import sys

import httpx


async def check_source(name: str, url: str, method: str = "GET"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/json,*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    try:
        async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True) as client:
            resp = await client.request(method, url, headers=headers)
            content_type = resp.headers.get("content-type", "")
            print(f"\n{'='*60}")
            print(f"📍 {name}")
            print(f"   URL: {url}")
            print(f"   Status: {resp.status_code}")
            print(f"   Content-Type: {content_type}")
            print(f"   Redirects: {len(resp.history)}")

            if resp.status_code == 200:
                if "json" in content_type:
                    data = resp.json()
                    preview = json.dumps(data, indent=2, ensure_ascii=False)[:2000]
                    print(f"   JSON keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                else:
                    preview = resp.text[:1500]
                print(f"\n   PREVIEW:\n{preview}")
            else:
                print(f"   ERROR: {resp.text[:500]}")
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"📍 {name}")
        print(f"   URL: {url}")
        print(f"   EXCEPTION: {e}")


async def main():
    sources = [
        ("TimePad API", "https://api.timepad.ru/v1/events?city_ids=78&limit=3&fields=location,description,categories"),
        ("Ponominalu API", "https://api.ponominalu.ru/v2/events?city_id=65"),
        ("Афиша НГС", "https://ngs.ru/afisha/"),
        ("Expomap", "https://expomap.ru/exhibition/list/?city=novosibirsk"),
        ("Мой Бизнес НСО", "https://mbnso.ru/events"),
        ("Академпарк", "https://academpark.com/events"),
        ("Сибярмарка", "https://sibfair.ru/exhibitions/"),
        ("ForumSib", "https://forumsib.ru"),
        ("Vibirai", "https://vibirai.ru/novosibirsk/"),
        ("2do2go", "https://2do2go.ru/novosibirsk/"),
        ("AllConferences", "https://allconferences.ru/novosibirsk/"),
        ("НГТУ", "https://www.nstu.ru/events"),
        ("ТПП НСО", "https://tppnso.ru/meropriyatiya/"),
    ]

    for name, url in sources:
        await check_source(name, url)


if __name__ == "__main__":
    asyncio.run(main())
