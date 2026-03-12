from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from config.db_conf import get_db
from crud import users
from models.users import User
from schemas.users import (
    UserAuthResponse,
    UserChangePasswordRequest,
    UserInfoResponse,
    UserRequest,
    UserUpdateRequest,
)
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists.")

    user = await users.create_user(db, user_data)
    token = await users.create_token(db, user.id)
    await db.commit()

    payload = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    return success_response(message="Registration successful.", data=payload)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    user = await users.authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    token = await users.create_token(db, user.id)
    await db.commit()

    payload = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    return success_response(message="Login successful.", data=payload)


@router.get("/info")
async def get_user_info(user: User = Depends(get_current_user)):
    return success_response(message="User info fetched.", data=UserInfoResponse.model_validate(user))


@router.put("/update")
async def update_user_info(
    user_data: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated_user = await users.update_user(db, user.id, user_data)
    await db.commit()
    return success_response(message="User updated.", data=UserInfoResponse.model_validate(updated_user))


@router.put("/password")
async def update_password(
    password_data: UserChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ok = await users.change_password(db, user, password_data.old_password, password_data.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect.",
        )
    await db.commit()
    return success_response(message="Password updated.")


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await users.delete_token(db, user.id)
    await db.commit()
    return success_response(message="Logged out.")
