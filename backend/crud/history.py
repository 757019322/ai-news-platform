from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.history import History
from models.news import News
from schemas.history import HistoryNewsItemResponse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def add_history(db: AsyncSession, user_id: int, news_id: int) -> None:
    stmt = select(History).where(History.user_id == user_id, History.news_id == news_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        existing.view_time = _utcnow()
        db.add(existing)
    else:
        db.add(History(user_id=user_id, news_id=news_id))

    await db.flush()


async def get_history_list(db: AsyncSession, user_id: int, offset: int, limit: int):
    stmt = (
        select(News, History.view_time.label("view_time"), History.id.label("history_id"))
        .join(History, History.news_id == News.id)
        .where(History.user_id == user_id)
        .order_by(History.view_time.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        news_obj = row[0]
        items.append(
            HistoryNewsItemResponse(
                id=news_obj.id,
                title=news_obj.title,
                description=getattr(news_obj, "description", None),
                image=news_obj.image,
                author=news_obj.author,
                category_id=news_obj.category_id,
                views=news_obj.views,
                publish_time=getattr(news_obj, "publish_time", None),
                history_id=row.history_id,
                view_time=row.view_time,
            )
        )
    return items


async def get_history_count(db: AsyncSession, user_id: int) -> int:
    stmt = select(func.count(History.id)).where(History.user_id == user_id)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def clear_history(db: AsyncSession, user_id: int) -> int:
    stmt = delete(History).where(History.user_id == user_id)
    result = await db.execute(stmt)
    return int(result.rowcount or 0)
