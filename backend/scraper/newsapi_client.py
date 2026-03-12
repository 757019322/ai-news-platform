from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

NEWSAPI_KEY = os.getenv("NEWS_API_KEY", "")
NEWSAPI_BASE = "https://newsapi.org/v2/top-headlines"

CATEGORY_MAP: dict[str, str] = {
    "Technology": "technology",
}


async def fetch_newsapi(category: str, page_size: int = 20) -> list[dict]:
    if not NEWSAPI_KEY:
        logger.warning("NEWS_API_KEY not set — skipping NewsAPI fetch.")
        return []

    newsapi_category = CATEGORY_MAP.get(category)
    if not newsapi_category:
        logger.warning("No NewsAPI category mapping for '%s'.", category)
        return []

    params = {
        "apiKey": NEWSAPI_KEY,
        "category": newsapi_category,
        "country": "us",
        "pageSize": page_size,
        "language": "en",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(NEWSAPI_BASE, params=params)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("NewsAPI request failed: %s", exc)
            return []

    data = resp.json()
    if data.get("status") != "ok":
        logger.error("NewsAPI error response: %s", data.get("message"))
        return []

    articles = []
    for item in data.get("articles", []):
        title = (item.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue

        raw_time = item.get("publishedAt") or ""
        try:
            publish_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            publish_time = datetime.now(timezone.utc)

        raw_image = (item.get("urlToImage") or "").strip()
        image = raw_image[:500] if raw_image else None

        content = item.get("content") or item.get("description") or title

        raw_author = (item.get("author") or item.get("source", {}).get("name") or "").strip()
        author = raw_author[:100] if raw_author else None

        articles.append({
            "title": title[:255],
            "description": (item.get("description") or "")[:500],
            "content": content,
            "image": image,
            "author": author,
            "publish_time": publish_time,
        })

    logger.info("NewsAPI returned %d articles for category '%s'.", len(articles), category)
    return articles
