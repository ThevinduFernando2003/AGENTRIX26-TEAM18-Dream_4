"""Chat + emergency screening + router output models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .common import INTENT


class ChatTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[str] = None


class EmergencyDecision(BaseModel):
    is_emergency: bool
    matched_terms: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class RouterOutput(BaseModel):
    """JSON-mode output from the basic chatbot orchestrator."""

    route: INTENT
    reply: str
    extracted: dict = Field(default_factory=dict)
