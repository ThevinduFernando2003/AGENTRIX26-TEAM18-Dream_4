"""Medicine and pharmacy-related Pydantic models - owned by Nisal.

This module contains all schemas for medicine tracking and price comparison flows.
"""

from typing import Literal

from pydantic import BaseModel, Field


class MedicineQuery(BaseModel):
    """Query for medicine prices across pharmacies."""
    user_id: int
    names: list[str]
    user_lat: float | None = None
    user_lng: float | None = None


class MedicinePriceItem(BaseModel):
    """Individual medicine price at a pharmacy."""
    medicine_id: int
    name: str
    price: float


class PharmacyQuote(BaseModel):
    """Complete quote from a single pharmacy for a set of medicines."""
    pharmacy_id: int
    pharmacy_name: str
    address: str | None
    items: list[MedicinePriceItem]
    total_cost: float
    distance_km: float | None = None
    missing: list[str] = Field(default_factory=list)


class MedicineQuoteResult(BaseModel):
    """Result of medicine price comparison across multiple pharmacies."""
    status: Literal["ok", "no_match", "no_location"]
    matched_names: list[str] = Field(default_factory=list)
    unmatched_names: list[str] = Field(default_factory=list)
    quotes: list[PharmacyQuote] = Field(default_factory=list)
    message: str


class OcrConfirmation(BaseModel):
    """User confirmation of OCR'd prescription text (prescription/OCR flow)."""
    prescription_id: int
    ocr_text: str
    user_edited_text: str | None = None
    confirmed: bool = False
