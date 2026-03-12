from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken
from schemas.users import UserRequest, UserUpdateRequest
from utils import security

TOKEN_TTL_DAYS = int(os.getenv("TOKEN_TTL_DAYS", "7"))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest) -> User:
    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_token(db: AsyncSession, user_id: int) -> str:
    raw_token = str(uuid.uuid4())
    hashed = _hash_token(raw_token)
    expires_at = _utcnow() + timedelta(days=TOKEN_TTL_DAYS)

    stmt = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(stmt)
    user_token = result.scalar_one_or_none()

    if user_token:
        user_token.token = hashed
        user_token.expires_at = expires_at
        db.add(user_token)
    else:
        user_token = UserToken(user_id=user_id, token=hashed, expires_at=expires_at)
        db.add(user_token)

    await db.flush()
    return raw_token


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not security.verify_password(password, user.password):
        return None
    return user


async def get_user_by_token(db: AsyncSession, raw_token: str) -> User | None:
    hashed = _hash_token(raw_token)
    stmt = select(UserToken).where(UserToken.token == hashed)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if not db_token:
        return None

    expires_at = db_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < _utcnow():
        return None

    stmt = select(User).where(User.id == db_token.user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, user_id: int, user_data: UserUpdateRequest) -> User:
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(
            **user_data.model_dump(
                exclude_unset=True,
                exclude_none=True,
            )
        )
    )
    result = await db.execute(stmt)
    await db.flush()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="User not found.")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> bool:
    if not security.verify_password(old_password, user.password):
        return False

    user.password = security.get_hash_password(new_password)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return True


async def delete_token(db: AsyncSession, user_id: int) -> None:
    stmt = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(stmt)
    token_row = result.scalar_one_or_none()
    if token_row:
        await db.delete(token_row)
        await db.flush()
