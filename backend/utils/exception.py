from __future__ import annotations

import os
import traceback
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = " → ".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        detail = f"{field}: {first.get('msg', 'Invalid value')}" if field else first.get("msg", "Validation error")
    else:
        detail = "Validation error."

    extra: Optional[list] = None
    if DEBUG_MODE:
        extra = errors

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "message": detail, "data": extra},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "data": None},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    raw = str(getattr(exc, "orig", exc))

    if "username_UNIQUE" in raw or "Duplicate entry" in raw:
        detail = "Username already exists."
    elif "phone_UNIQUE" in raw:
        detail = "Phone number already exists."
    elif "uniq_user_news" in raw:
        detail = "Already favorited."
    elif "FOREIGN KEY" in raw:
        detail = "Referenced entity does not exist."
    else:
        detail = "Constraint violation. Please verify your input."

    extra: Optional[dict[str, Any]] = None
    if DEBUG_MODE:
        extra = {"error_type": "IntegrityError", "error_detail": raw, "path": str(request.url)}

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"code": 400, "message": detail, "data": extra},
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    extra: Optional[dict[str, Any]] = None
    if DEBUG_MODE:
        extra = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "Database operation failed.", "data": extra},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    extra: Optional[dict[str, Any]] = None
    if DEBUG_MODE:
        extra = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": traceback.format_exc(),
            "path": str(request.url),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "Internal server error.", "data": extra},
    )
