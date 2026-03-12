from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import history as history_crud
from models.users import User
from schemas.history import HistoryAddRequest, HistoryListResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add")
async def add_history(
    data: HistoryAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await history_crud.add_history(db, user.id, data.news_id)
    await db.commit()
    return success_response(message="History recorded.")


@router.get("/list")
async def list_history(
    page: int = 1,
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be >= 1")

    offset = (page - 1) * page_size
    items = await history_crud.get_history_list(db, user.id, offset, page_size)
    total = await history_crud.get_history_count(db, user.id)
    has_more = (offset + len(items)) < total

    return success_response(
        message="History fetched.",
        data=HistoryListResponse(list=items, total=total, has_more=has_more),
    )


@router.delete("/clear")
async def clear_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await history_crud.clear_history(db, user.id)
    await db.commit()
    return success_response(message="History cleared.")
