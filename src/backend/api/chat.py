"""Chat API — full RAG pipeline: query → retrieve → generate → cite."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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
# Helpers
# ---------------------------------------------------------------------------

async def _build_rag_pipeline(body: ChatMessageIn, session: AsyncSession):
    """Shared RAG pipeline: build vehicle context, retrieve, build prompt.

    Returns (vehicle_type, vehicle_name, rag_ctx, system_prompt).
    """
    vehicle_type = settings.default_vehicle
    vehicle_context_str = ""

    if body.vehicle_id is not None:
        try:
            ctx = await vehicle_service.build_context(session, body.vehicle_id)
            vehicle_type = ctx.vehicle_type
            vehicle_context_str = ctx.to_prompt_string()
            vehicle_name = ctx.vehicle_name
        except ValueError:
            raise HTTPException(status_code=404, detail="Vehicle not found")
    else:
        ctx = vehicle_service.build_context_from_config(vehicle_type)
        vehicle_context_str = ctx.to_prompt_string()
        vehicle_name = vehicle_type.upper()

    rag_ctx = rag_service.assemble_context(
        query=body.message,
        vehicle_type=vehicle_type,
        vehicle_context=vehicle_context_str,
    )

    system_prompt = chat_service.build_system_prompt(
        vehicle_name=vehicle_name,
        vehicle_context=vehicle_context_str,
        retrieved_context=rag_ctx.formatted,
    )

    return vehicle_type, vehicle_name, rag_ctx, system_prompt


async def _persist_messages(
    session: AsyncSession,
    vehicle_id: int | None,
    user_message: str,
    assistant_content: str,
    rag_chunks: list,
    tokens_used: int = 0,
) -> None:
    """Save user + assistant messages to the database."""
    from backend.models.database import ChatMessage

    # For messages without a vehicle_id, we skip persistence since the
    # ChatMessage model requires a vehicle_id foreign key.
    if vehicle_id is None:
        return

    now = datetime.utcnow()

    user_msg = ChatMessage(
        vehicle_id=vehicle_id,
        timestamp=now,
        role="user",
        content=user_message,
    )
    session.add(user_msg)

    context_data = [
        {"source": c.source, "category": c.category, "score": c.score}
        for c in rag_chunks
    ] if rag_chunks else None

    assistant_msg = ChatMessage(
        vehicle_id=vehicle_id,
        timestamp=now,
        role="assistant",
        content=assistant_content,
        context=context_data,
        tokens_used=tokens_used,
    )
    session.add(assistant_msg)
    await session.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/message", response_model=ChatResponse)
async def send_message(
    body: ChatMessageIn,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Full RAG pipeline: retrieve context → build prompt → generate response."""

    vehicle_type, vehicle_name, rag_ctx, system_prompt = await _build_rag_pipeline(body, session)

    # Generate
    try:
        llm_resp = await chat_service.generate(
            prompt=body.message,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        raise HTTPException(status_code=503, detail="LLM service unavailable")

    # Build source references
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

    # Persist to database
    await _persist_messages(
        session,
        body.vehicle_id,
        body.message,
        llm_resp.content,
        rag_ctx.chunks,
        llm_resp.tokens_used,
    )

    return ChatResponse(
        response=llm_resp.content,
        sources=sources,
        tokens_used=llm_resp.tokens_used,
        model=llm_resp.model,
    )


@router.post("/message/stream")
async def send_message_stream(
    body: ChatMessageIn,
    session: AsyncSession = Depends(get_session),
):
    """SSE streaming RAG pipeline.

    RAG retrieval happens synchronously before streaming begins.
    LLM tokens stream as ``data:`` events.  Sources are sent as a
    final ``event: sources`` SSE event.
    """
    vehicle_type, vehicle_name, rag_ctx, system_prompt = await _build_rag_pipeline(body, session)

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

    async def event_generator() -> AsyncIterator[str]:
        full_response = ""
        try:
            async for token in chat_service.generate_stream(
                prompt=body.message,
                system_prompt=system_prompt,
            ):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as exc:
            logger.error("Streaming generation failed: %s", exc)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        # Send sources as final event
        sources_data = [s.model_dump() for s in sources]
        yield f"event: sources\ndata: {json.dumps({'sources': sources_data})}\n\n"

        # Send done event
        yield f"event: done\ndata: {json.dumps({'tokens_used': len(full_response)})}\n\n"

        # Persist to database (best-effort, after stream completes)
        try:
            await _persist_messages(
                session,
                body.vehicle_id,
                body.message,
                full_response,
                rag_ctx.chunks,
            )
        except Exception as exc:
            logger.warning("Failed to persist streamed message: %s", exc)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
