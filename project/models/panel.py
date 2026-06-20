"""Panel/Report-related Pydantic models - owned by Chanupa.

This module contains schemas for Tier 2 specialist panel and report review flows.
"""

from typing import Optional

from pydantic import BaseModel, Field

from .common import SPECIALIST


class SpecialistOpinion(BaseModel):
    """Opinion from a single specialist reviewing a report."""
    specialist_type: SPECIALIST
    findings: str
    confidence: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    report_id: Optional[int] = None


class ConsensusReport(BaseModel):
    """Moderator's synthesis of specialist opinions."""
    summary: str
    points_of_agreement: list[str]
    points_of_disagreement: list[str]
    disclaimer: str
    report_id: Optional[int] = None


class PanelResult(BaseModel):
    """Bundled output of specialist panel + moderator for the UI."""
    report_id: int
    opinions: list[SpecialistOpinion]
    consensus: ConsensusReport
    used_llm: bool
