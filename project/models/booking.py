"""Booking-flow models — request, response, and confirmation shapes."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
