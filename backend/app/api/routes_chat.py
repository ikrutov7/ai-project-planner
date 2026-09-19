"""AI chat route."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agent import AgentService
from app.api.schemas import ChatRequest, ChatResponse, ChatMessageOut
from app.dependencies import get_plan_service
from app.services.plan_service import PlanService

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    service: PlanService = Depends(get_plan_service),
) -> ChatResponse:
    agent = AgentService(service)
    result = agent.handle_chat(body.message, conversation_id=body.conversation_id)
    return ChatResponse(
        conversation_id=result.conversation_id,
        message=ChatMessageOut(role=result.message.role, content=result.message.content),
        plan=result.plan,
        changes=result.changes,
        tool_trace=result.tool_trace,
        mode=result.mode,
    )
