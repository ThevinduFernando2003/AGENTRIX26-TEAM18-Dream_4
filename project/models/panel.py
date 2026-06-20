"""Specialist Panel + Moderator models (Tier 2)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .common import SPECIALIST


class SpecialistOpinion(BaseModel):
    specialist_type: SPECIALIST
    findings: str
    confidence: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    # report_id is populated by run_panel() at persistence time, not by the LLM.
    report_id: Optional[int] = None


class ConsensusReport(BaseModel):
    summary: str
    points_of_agreement: list[str]
    points_of_disagreement: list[str]
    disclaimer: str
    report_id: Optional[int] = None


class PanelResult(BaseModel):
    """Bundled output of run_panel + Moderator for the UI."""

    report_id: int
    opinions: list[SpecialistOpinion]
    consensus: ConsensusReport
    used_llm: bool
