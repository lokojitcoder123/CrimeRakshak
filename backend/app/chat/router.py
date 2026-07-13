"""Conversational chat API (Block 1 core).

``POST /chat`` runs a user turn through the tool-calling agent and returns a
grounded answer with provenance. Conversation memory is kept in-process per
``conversation_id`` for now (durable Postgres persistence + PDF export arrive
in a later phase).

The endpoint requires an authenticated active user, so the agent's data access
inherits the caller's identity for audit purposes.
"""
from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends

from app.chat.agent import run_agent
from app.chat.schemas import ChatRequest, ChatResponse
from app.core.dependencies import get_current_active_user
from app.core.logging import get_logger
from app.models.rbac import User

logger = get_logger("chat.api")

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory conversation store: {conversation_id: [message dicts]}.
# Only user/assistant/tool turns are stored (no system prompt).
_CONVERSATIONS: dict[str, list[dict]] = defaultdict(list)
# Trim history fed back to the model to the most recent N messages.
_HISTORY_WINDOW = 20


@router.post("", response_model=ChatResponse, summary="Ask the crime-intelligence assistant")
def chat(payload: ChatRequest, current_user: User = Depends(get_current_active_user)) -> ChatResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    history = _CONVERSATIONS[conversation_id][-_HISTORY_WINDOW:]

    logger.info("chat turn user=%s conv=%s", current_user.username, conversation_id)
    turn = run_agent(payload.message, history=history)

    _CONVERSATIONS[conversation_id].extend(turn.new_messages)

    return ChatResponse(
        conversation_id=conversation_id,
        answer=turn.answer,
        sources=turn.sources,
        tool_calls=turn.tool_calls,
    )
