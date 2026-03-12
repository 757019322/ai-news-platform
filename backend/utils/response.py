from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None, code: int = 200) -> JSONResponse:
    content = {
        "code": code,
        "message": message,
        "data": data,
    }
    return JSONResponse(content=jsonable_encoder(content), status_code=code)


def error_response(message: str, code: int = 400, data=None) -> JSONResponse:
    content = {
        "code": code,
        "message": message,
        "data": data,
    }
    return JSONResponse(content=jsonable_encoder(content), status_code=code)
