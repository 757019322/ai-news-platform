from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import AsyncSessionLocal
from models.news import Category, News
from scraper.newsapi_client import fetch_newsapi
from scraper.rss_client import fetch_rss
from scraper.sources import RSS_SOURCES

logger = logging.getLogger(__name__)


async def _get_or_create_category(db: AsyncSession, name: str) -> Category:
    stmt = select(Category).where(Category.name == name)
    result = await db.execute(stmt)
    category = result.scalar_one_or_none()

    if not category:
        category = Category(name=name, sort_order=0)
        db.add(category)
        await db.flush()
        logger.info("Created new category: %s", name)

    return category


async def _insert_articles(
    db: AsyncSession,
    articles: list[dict],
    category_id: int,
    existing_titles: set[str],
) -> int:
    inserted = 0
    for article in articles:
        title = article["title"]
        if title in existing_titles:
            continue

        news = News(
            title=title,
            description=article.get("description"),
            content=article["content"],
            image=article.get("image"),
            author=article.get("author"),
            publish_time=article.get("publish_time", datetime.now(timezone.utc)),
            category_id=category_id,
            views=0,
        )

        try:
            async with db.begin_nested():
                db.add(news)
                await db.flush()
            existing_titles.add(title)
            inserted += 1
        except Exception as exc:
            logger.warning(
                "Skipped article due to error (%s): %s",
                type(exc).__name__,
                title,
            )

    return inserted


async def run_scraper() -> None:
    logger.info("Scraper started at %s UTC", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))

    async with AsyncSessionLocal() as db:
        async with db.begin():
            for category_name, rss_urls in RSS_SOURCES.items():
                category = await _get_or_create_category(db, category_name)

                existing_stmt = select(News.title).where(News.category_id == category.id)
                existing_result = await db.execute(existing_stmt)
                existing_titles: set[str] = {row[0] for row in existing_result.all()}

                rss_tasks = [fetch_rss(url) for url in rss_urls]
                newsapi_task = fetch_newsapi(category_name)

                results = await asyncio.gather(newsapi_task, *rss_tasks, return_exceptions=True)

                all_articles: list[dict] = []
                for result in results:
                    if isinstance(result, Exception):
                        logger.error("Fetch failed: %s", result)
                    else:
                        all_articles.extend(result)

                if not all_articles:
                    logger.warning("No articles fetched for category '%s'.", category_name)
                    continue

                count = await _insert_articles(db, all_articles, category.id, existing_titles)
                logger.info(
                    "Category '%s': fetched %d total, inserted %d new articles.",
                    category_name, len(all_articles), count,
                )

    logger.info("Scraper finished.")
