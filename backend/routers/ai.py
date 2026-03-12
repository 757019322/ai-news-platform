from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.news import News
from services.embedding import embed_text, get_index
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI"])


def _serialize(articles: list[News]) -> list[dict]:
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "image": a.image,
            "author": a.author,
            "categoryId": a.category_id,
            "views": a.views,
            "publishTime": a.publish_time.isoformat() if a.publish_time else None,
        }
        for a in articles
    ]


async def _fetch_articles(db: AsyncSession, ids: list[int]) -> list[News]:
    if not ids:
        return []
    stmt = select(News).where(News.id.in_(ids))
    rows = (await db.execute(stmt)).scalars().all()
    id_to_article = {a.id: a for a in rows}
    return [id_to_article[i] for i in ids if i in id_to_article]


@router.get("/search")
async def semantic_search(
    q: str = Query(..., min_length=1, description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty or whitespace.")

    index = get_index()
    if index.size == 0:
        return success_response(
            message="Search index not ready yet.",
            data={"list": [], "total": 0},
        )

    try:
        query_vec = await embed_text(q)
    except Exception as exc:
        logger.error("Embedding failed for query '%s': %s", q, exc)
        raise HTTPException(status_code=503, detail="Search service unavailable.")

    ids = index.search(query_vec, k=limit)
    articles = await _fetch_articles(db, ids)

    return success_response(
        message="Search results fetched.",
        data={"list": _serialize(articles), "total": len(articles), "query": q},
    )


@router.get("/related")
async def related_articles(
    news_id: int = Query(..., alias="newsId"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(News).where(News.id == news_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if article is None:
        raise HTTPException(status_code=404, detail="Article not found.")

    if article.embedding is None:
        stmt = (
            select(News)
            .where(News.category_id == article.category_id, News.id != news_id)
            .order_by(News.publish_time.desc())
            .limit(limit)
        )
        fallback = (await db.execute(stmt)).scalars().all()
        return success_response(
            message="Related articles fetched (category fallback).",
            data={"list": _serialize(list(fallback)), "total": len(fallback)},
        )

    try:
        vec = json.loads(article.embedding)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid embedding data.")

    index = get_index()
    ids = index.search(vec, k=limit + 1)
    ids = [i for i in ids if i != news_id][:limit]

    articles = await _fetch_articles(db, ids)

    return success_response(
        message="Related articles fetched.",
        data={"list": _serialize(articles), "total": len(articles)},
    )
