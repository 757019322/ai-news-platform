from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub("", text).strip()


def _parse_date(entry: feedparser.FeedParserDict) -> datetime:
    if entry.get("published_parsed"):
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    raw = entry.get("published") or ""
    if raw:
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc)
        except Exception:
            pass

    return datetime.now(timezone.utc)


def _extract_image(entry: feedparser.FeedParserDict) -> str | None:
    url = None

    if entry.get("media_thumbnail"):
        url = entry.media_thumbnail[0].get("url")
    elif entry.get("media_content"):
        url = entry.media_content[0].get("url")
    elif entry.get("links"):
        for link in entry.links:
            if link.get("type", "").startswith("image/"):
                url = link.get("href")
                break

    if url:
        return url.strip()[:500]
    return None


async def fetch_rss(feed_url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(
                feed_url,
                headers={"User-Agent": "NewsApp/1.0 RSS reader (educational project)"},
            )
            resp.raise_for_status()
            raw_xml = resp.text
        except httpx.HTTPError as exc:
            logger.error("RSS fetch failed for %s: %s", feed_url, exc)
            return []

    feed = feedparser.parse(raw_xml)

    if feed.bozo and not feed.entries:
        logger.warning("RSS parse error for %s: %s", feed_url, feed.bozo_exception)
        return []

    articles = []
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        if not title:
            continue

        content_blocks = entry.get("content", [])
        content = content_blocks[0].get("value", "") if content_blocks else ""
        if not content:
            content = entry.get("summary") or title

        description = _strip_html(entry.get("summary") or "")[:500]

        raw_author = (entry.get("author") or feed.feed.get("title") or "").strip()
        author = raw_author[:100] if raw_author else None

        articles.append({
            "title": title[:255],
            "description": description,
            "content": content,
            "image": _extract_image(entry),
            "author": author,
            "publish_time": _parse_date(entry),
        })

    logger.info("RSS feed %s returned %d articles.", feed_url, len(articles))
    return articles
