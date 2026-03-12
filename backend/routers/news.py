from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import news as news_crud
from utils.response import success_response

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories")
async def get_categories(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    categories = await news_crud.get_categories(db, skip, limit)
    data = [{"id": c.id, "name": c.name} for c in categories]
    return success_response(message="Categories fetched.", data=data)


@router.get("/list")
async def get_news_list(
    category_id: int = Query(..., alias="categoryId"),
    page: int = 1,
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")

    offset = (page - 1) * page_size
    items = await news_crud.get_news_list(db, category_id, offset, page_size)
    total = await news_crud.get_news_count(db, category_id)
    has_more = (offset + len(items)) < total

    return success_response(
        message="News list fetched.",
        data={"list": items, "total": total, "hasMore": has_more},
    )


@router.get("/detail")
async def get_news_detail(news_id: int = Query(..., alias="id"), db: AsyncSession = Depends(get_db)):
    article = await news_crud.get_news_detail(db, news_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News item not found.")

    await news_crud.increase_news_views(db, article.id)
    await db.commit()

    related = await news_crud.get_related_news(db, article.id, article.category_id)
    related_payload = [
        {"id": r.id, "title": r.title, "image": r.image}
        for r in related
    ]

    payload = {
        "id": article.id,
        "title": article.title,
        "description": article.description,
        "content": article.content,
        "image": article.image,
        "author": article.author,
        "publishTime": article.publish_time,
        "categoryId": article.category_id,
        "views": article.views + 1,
        "relatedNews": related_payload,
    }
    return success_response(message="News detail fetched.", data=payload)
