from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scraper.runner import run_scraper
from services.embedding import embed_all_news

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _scrape_and_embed() -> None:
    await run_scraper()
    await embed_all_news()


def start_scheduler() -> None:
    _scheduler.add_job(
        _scrape_and_embed,
        trigger=CronTrigger(hour="6,18", minute=0, timezone="UTC"),
        id="news_scraper",
        name="Fetch and store latest tech news",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("Scheduler started — scraper will run at 06:00 and 18:00 UTC.")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
