#!/usr/bin/env python3
"""Глубокий анализ HTML-структуры источников — находит все потенциальные карточки событий."""
import asyncio
import json
import re

import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

SOURCES = [
    ("Vibirai", "https://novosibirsk.vibirai.ru/afisha"),
    ("Мой Бизнес НСО", "https://mbnso.ru/events/"),
    ("Академпарк", "https://academpark.com/events/"),
]


def analyze_cards(soup, source_name):
    """Анализирует HTML и ищет возможные карточки событий."""
    results = []
    # Ищем все ссылки с текстом похожим на заголовки событий
    date_pattern = re.compile(r"\d{1,2}\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)", re.IGNORECASE)

    links = soup.find_all("a", href=True)
    for a in links:
        text = a.get_text(strip=True)
        href = a.get("href", "")
        if len(text) > 10 and not href.startswith("#") and "javascript" not in href:
            # Проверяем родительский контейнер
            parent = a.find_parent(["article", "section", "div", "li"])
            parent_classes = parent.get("class", []) if parent else []
            parent_id = parent.get("id", "") if parent else ""

            results.append({
                "title": text[:80],
                "href": href,
                "parent_tag": parent.name if parent else "?",
                "parent_classes": parent_classes[:3],
                "has_date_in_parent": bool(date_pattern.search(parent.get_text() if parent else "")),
            })

    # Сортируем: сначала те, у кого есть дата рядом
    results.sort(key=lambda x: not x["has_date_in_parent"])
    return results[:30]


async def fetch_and_analyze(name, url):
    print(f"\n{'='*70}")
    print(f"📍 {name}")
    print(f"   URL: {url}")
    print()

    try:
        async with httpx.AsyncClient(timeout=20, verify=False, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(separator=" ", strip=True)

            print(f"   Status: {resp.status_code}")
            print(f"   HTML size: {len(resp.text)} chars")
            print(f"   Text size: {len(text)} chars")
            print()

            # 1. Ищем любые элементы с датами
            date_elements = []
            for el in soup.find_all(string=re.compile(r"\d{1,2}\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)\s+\d{4}", re.IGNORECASE)):
                parent = el.find_parent(["div", "article", "section", "li"])
                if parent and parent.get("class"):
                    date_elements.append({
                        "text": el.strip()[:100],
                        "parent_tag": parent.name,
                        "parent_classes": parent.get("class", []),
                    })
            print(f"   🔍 Элементов с датами: {len(date_elements)}")
            for de in date_elements[:5]:
                print(f"      - {de['text']}  ({de['parent_tag']}.{de['parent_classes'][:2]})")

            # 2. Ищем заголовки h2/h3/h4 с текстом > 15 символов
            headings = []
            for tag in ["h2", "h3", "h4"]:
                for el in soup.find_all(tag):
                    txt = el.get_text(strip=True)
                    if len(txt) > 15:
                        headings.append(txt[:80])
            print(f"   🔍 Заголовков (h2-h4, >15 символов): {len(headings)}")
            for h in headings[:8]:
                print(f"      - {h}")

            # 3. Все элементы с популярными event-классами
            event_classes = [
                "event", "card", "item", "post", "news", "afisha",
                "list-item", "catalog-card", "product-card", "preview",
            ]
            for cls in event_classes:
                els = soup.find_all(class_=re.compile(cls, re.I))
                if els:
                    print(f"   🔍 Элементов с class~'{cls}': {len(els)}")
                    # Покажем первый
                    first_classes = els[0].get("class", [])
                    first_tag = els[0].name
                    first_text = els[0].get_text(strip=True)[:60]
                    print(f"      Первый: <{first_tag} class={first_classes[:3]}> {first_text}")

            # 4. Анализ карточек
            cards = analyze_cards(soup, name)
            if cards:
                print(f"\n   🎯 Потенциальные карточки событий (первые 8):")
                for c in cards[:8]:
                    date_mark = "📅" if c["has_date_in_parent"] else "  "
                    print(f"      {date_mark} [{c['parent_tag']}.{'.'.join(map(str, c['parent_classes'][:2]))}]")
                    print(f"            {c['title']}")
                    print(f"            {c['href'][:80]}")
            else:
                print(f"\n   ⚠️  Карточек событий не найдено")

            # 5. Сохраняем HTML для анализа
            with open(f"/tmp/debug_{name.lower().replace(' ', '_')}.html", "w") as f:
                f.write(resp.text)
            print(f"\n   💾 HTML сохранён: /tmp/debug_{name.lower().replace(' ', '_')}.html")

    except Exception as e:
        print(f"   ❌ Ошибка: {e}")


async def main():
    for name, url in SOURCES:
        await fetch_and_analyze(name, url)
    print(f"\n{'='*70}")
    print("\n✅ Анализ завершён. Файлы сохранены в /tmp/")
    print("   Чтобы прочитать конкретный файл, выполните:")
    print("   cat /tmp/debug_*.html | head -200")


if __name__ == "__main__":
    asyncio.run(main())
