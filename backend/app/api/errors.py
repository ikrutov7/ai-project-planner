"""HTTP error helpers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError


STATUS_BY_CODE = {
    "TASK_NOT_FOUND": 404,
    "PLAN_NOT_FOUND": 404,
    "ASSIGNEE_NOT_FOUND": 404,
    "CIRCULAR_DEPENDENCY": 400,
    "INVALID_DEPENDENCY": 400,
    "UNKNOWN_PREDECESSOR": 400,
    "INVALID_DURATION": 400,
    "DUPLICATE_TASK": 400,
    "INVALID_EXCEL": 400,
    "INVALID_INPUT": 422,
    "VERSION_CONFLICT": 409,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        status = STATUS_BY_CODE.get(exc.code, 400)
        return JSONResponse(status_code=status, content={"error": exc.to_dict()})
