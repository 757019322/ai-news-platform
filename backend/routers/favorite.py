from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import favorite as favorite_crud
from models.users import User
from schemas.favorite import FavoriteCheckResponse, FavoriteListResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/favorite", tags=["favorite"])


@router.get("/check")
async def check_favorite(
    news_id: int = Query(..., alias="newsId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exists = await favorite_crud.check_favorite(db, user.id, news_id)
    return success_response(
        message="Favorite status fetched.",
        data=FavoriteCheckResponse(isFavorite=exists),
    )


@router.post("/add")
async def add_favorite(
    news_id: int = Body(..., embed=True, alias="newsId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await favorite_crud.add_favorite(db, user.id, news_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already favorited.",
        )
    await db.commit()
    return success_response(message="Added to favorites.")


@router.delete("/remove")
async def remove_favorite(
    news_id: int = Query(..., alias="newsId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await favorite_crud.remove_favorite(db, user.id, news_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found.",
        )
    await db.commit()
    return success_response(message="Removed from favorites.")


@router.get("/list")
async def list_favorites(
    page: int = 1,
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="page must be >= 1",
        )

    offset = (page - 1) * page_size
    items = await favorite_crud.get_favorite_list(db, user.id, offset, page_size)
    total = await favorite_crud.get_favorite_count(db, user.id)
    has_more = (offset + len(items)) < total

    return success_response(
        message="Favorites fetched.",
        data=FavoriteListResponse(list=items, total=total, has_more=has_more),
    )
