from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import Category, News


async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    stmt = select(Category).order_by(Category.sort_order, Category.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_news_list(db: AsyncSession, category_id: int, skip: int = 0, limit: int = 10):
    stmt = (
        select(News)
        .where(News.category_id == category_id)
        .order_by(News.publish_time.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_news_count(db: AsyncSession, category_id: int) -> int:
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def get_news_detail(db: AsyncSession, news_id: int) -> News | None:
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increase_news_views(db: AsyncSession, news_id: int) -> None:
    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    await db.execute(stmt)


async def get_related_news(db: AsyncSession, news_id: int, category_id: int, limit: int = 5):
    stmt = (
        select(News)
        .where(News.category_id == category_id, News.id != news_id)
        .order_by(News.publish_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
