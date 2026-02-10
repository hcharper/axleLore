"""Chat API — full RAG pipeline: query → retrieve → generate → cite."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.session import get_session
from backend.services import chat_service, rag_service, vehicle_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatMessageIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    vehicle_id: Optional[int] = None


class SourceRef(BaseModel):
    index: int
    source: str
    category: str
    score: float
    title: str = ""


class ChatResponse(BaseModel):
    response: str
    sources: list[SourceRef] = []
    tokens_used: int = 0
    model: str = ""


class ChatHistoryItem(BaseModel):
    role: str
    content: str
    timestamp: str
    sources: list[SourceRef] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatMessageIn,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Full RAG pipeline: retrieve context → build prompt → generate response."""

    vehicle_type = settings.default_vehicle
    vehicle_context_str = ""

    # 1. Build vehicle context
    if body.vehicle_id is not None:
        try:
            ctx = await vehicle_service.build_context(session, body.vehicle_id)
            vehicle_type = ctx.vehicle_type
            vehicle_context_str = ctx.to_prompt_string()
        except ValueError:
            raise HTTPException(status_code=404, detail="Vehicle not found")
    else:
        # Fallback to config-only context
        ctx = vehicle_service.build_context_from_config(vehicle_type)
        vehicle_context_str = ctx.to_prompt_string()

    # 2. RAG retrieval
    rag_ctx = rag_service.assemble_context(
        query=body.message,
        vehicle_type=vehicle_type,
        vehicle_context=vehicle_context_str,
    )

    # 3. Build prompt
    system_prompt = chat_service.build_system_prompt(
        vehicle_name=ctx.vehicle_name if body.vehicle_id else vehicle_type.upper(),
        vehicle_context=vehicle_context_str,
        retrieved_context=rag_ctx.formatted,
    )

    # 4. Generate
    try:
        llm_resp = await chat_service.generate(
            prompt=body.message,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise HTTPException(status_code=503, detail="LLM service unavailable")

    # 5. Build source references
    sources = [
        SourceRef(
            index=i + 1,
            source=c.source,
            category=c.category,
            score=round(c.score, 3),
            title=c.metadata.get("title", ""),
        )
        for i, c in enumerate(rag_ctx.chunks)
    ]

    return ChatResponse(
        response=llm_resp.content,
        sources=sources,
        tokens_used=llm_resp.tokens_used,
        model=llm_resp.model,
    )


@router.get("/history", response_model=list[ChatHistoryItem])
async def get_history(
    vehicle_id: Optional[int] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> list[ChatHistoryItem]:
    """Retrieve chat history from the database."""
    from sqlalchemy import select, desc
    from backend.models.database import ChatMessage

    stmt = select(ChatMessage).order_by(desc(ChatMessage.timestamp)).limit(limit)
    if vehicle_id is not None:
        stmt = stmt.where(ChatMessage.vehicle_id == vehicle_id)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    return [
        ChatHistoryItem(
            role=r.role,
            content=r.content,
            timestamp=r.timestamp.isoformat(),
        )
        for r in rows
    ]


@router.delete("/history")
async def clear_history(
    vehicle_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete chat history."""
    from sqlalchemy import delete
    from backend.models.database import ChatMessage

    stmt = delete(ChatMessage)
    if vehicle_id is not None:
        stmt = stmt.where(ChatMessage.vehicle_id == vehicle_id)
    await session.execute(stmt)
    await session.commit()
    return {"status": "ok", "message": "History cleared"}
