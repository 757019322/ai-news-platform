from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _GenderMixin(BaseModel):
    gender: Optional[str] = Field(None)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("male", "female", "unknown"):
            raise ValueError("gender must be one of: male, female, unknown")
        return v


class UserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class UserInfoBase(_GenderMixin):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=500)


class UserInfoResponse(UserInfoBase):
    id: int
    username: str
    phone: Optional[str] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class UserAuthResponse(BaseModel):
    token: str
    user_info: UserInfoResponse = Field(..., alias="userInfo")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class UserUpdateRequest(_GenderMixin):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)


class UserChangePasswordRequest(BaseModel):
    old_password: str = Field(..., alias="oldPassword")
    new_password: str = Field(..., min_length=6, alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)
