from __future__ import annotations

from sqlalchemy import delete, func, select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from models.favorite import Favorite
from models.news import News
from schemas.favorite import FavoriteNewsItemResponse


async def check_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    stmt = select(exists().where(Favorite.user_id == user_id, Favorite.news_id == news_id))
    result = await db.execute(stmt)
    return bool(result.scalar())


async def add_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    already = await check_favorite(db, user_id, news_id)
    if already:
        return False
    fav = Favorite(user_id=user_id, news_id=news_id)
    db.add(fav)
    await db.flush()
    return True


async def remove_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(stmt)
    return (result.rowcount or 0) > 0


async def get_favorite_list(db: AsyncSession, user_id: int, offset: int, limit: int):
    stmt = (
        select(News, Favorite.created_at.label("favorite_time"), Favorite.id.label("favorite_id"))
        .join(Favorite, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        news_obj = row[0]
        items.append(
            FavoriteNewsItemResponse(
                id=news_obj.id,
                title=news_obj.title,
                description=getattr(news_obj, "description", None),
                image=news_obj.image,
                author=news_obj.author,
                category_id=news_obj.category_id,
                views=news_obj.views,
                publish_time=getattr(news_obj, "publish_time", None),
                favorite_id=row.favorite_id,
                favorite_time=row.favorite_time,
            )
        )
    return items


async def get_favorite_count(db: AsyncSession, user_id: int) -> int:
    stmt = select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


async def clear_favorites(db: AsyncSession, user_id: int) -> int:
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    return int(result.rowcount or 0)
