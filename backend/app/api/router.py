"""Aggregate API router."""

from fastapi import APIRouter

from app.api.routes_chat import router as chat_router
from app.api.routes_excel import router as excel_router
from app.api.routes_health import router as health_router
from app.api.routes_plan import router as plan_router
from app.api.routes_tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(plan_router)
api_router.include_router(tasks_router)
api_router.include_router(excel_router)
api_router.include_router(chat_router)
