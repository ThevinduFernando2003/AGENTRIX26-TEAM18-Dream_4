"""All Pydantic models for MedBridge AI live here.

Tier 1 uses Booking, Medicine, Emergency, ChatTurn.
Tier 2 stubs (SpecialistOpinion, ConsensusReport) are defined now so
schemas don't churn when those agents land.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

INTENT = Literal["booking", "medicine", "report_review", "emergency", "general"]


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


class BookingRequest(BaseModel):
    user_id: int
    doctor_name: Optional[str] = None
    specialty: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM


class AlternativeSlot(BaseModel):
    slot_id: int
    doctor_id: int
    doctor_name: str
    facility_name: str
    date: str
    time: str
    channeling_fee: float


class BookingConfirmation(BaseModel):
    appointment_id: int
    slot_id: int
    doctor_name: str
    facility_name: str
    date: str
    time: str
    channeling_fee: float


class BookingResponse(BaseModel):
    status: Literal["booked", "alternatives", "not_found", "needs_info"]
    confirmation: Optional[BookingConfirmation] = None
    alternatives: list[AlternativeSlot] = Field(default_factory=list)
    message: str


class MedicineQuery(BaseModel):
    user_id: int
    names: list[str]
    user_lat: Optional[float] = None
    user_lng: Optional[float] = None


class MedicinePriceItem(BaseModel):
    medicine_id: int
    name: str
    price: float


class PharmacyQuote(BaseModel):
    pharmacy_id: int
    pharmacy_name: str
    address: Optional[str]
    items: list[MedicinePriceItem]
    total_cost: float
    distance_km: Optional[float] = None
    missing: list[str] = Field(default_factory=list)
    # Oldest updated_at among quoted in-stock lines (honest freshness).
    updated_at: Optional[str] = None
    freshness_label: Optional[str] = None


class MedicineQuoteResult(BaseModel):
    status: Literal["ok", "no_match", "no_location"]
    matched_names: list[str] = Field(default_factory=list)
    unmatched_names: list[str] = Field(default_factory=list)
    quotes: list[PharmacyQuote] = Field(default_factory=list)
    message: str


# ---- Tier 2 ----

SPECIALIST = Literal["cardiology", "internal_medicine", "radiology"]


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


class OcrConfirmation(BaseModel):
    prescription_id: int
    ocr_text: str
    user_edited_text: Optional[str] = None
    confirmed: bool = False
