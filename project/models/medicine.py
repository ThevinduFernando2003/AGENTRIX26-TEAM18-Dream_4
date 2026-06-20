"""Medicine tracker + prescription OCR models.

`OcrConfirmation` lives here because the prescription confirmation step
flows directly into the pharmacy comparison — same vertical.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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


class MedicineQuoteResult(BaseModel):
    status: Literal["ok", "no_match", "no_location"]
    matched_names: list[str] = Field(default_factory=list)
    unmatched_names: list[str] = Field(default_factory=list)
    quotes: list[PharmacyQuote] = Field(default_factory=list)
    message: str


class OcrConfirmation(BaseModel):
    prescription_id: int
    ocr_text: str
    user_edited_text: Optional[str] = None
    confirmed: bool = False
