"""Pydantic request/response models for the chat API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural-language question.")
    conversation_id: Optional[str] = Field(
        None, description="Omit to start a new conversation; pass to continue one."
    )


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: List[str] = Field(default_factory=list, description="Grounding provenance (SQL/tools used).")
    tool_calls: int = 0
