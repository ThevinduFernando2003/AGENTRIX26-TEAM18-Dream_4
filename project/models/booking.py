"""Booking-related Pydantic models - owned by Thevindu.

This module contains all schemas for the booking flow including:
- Booking requests and responses
- Alternative slot suggestions
- Booking confirmations
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BookingRequest(BaseModel):
    """User's initial booking request, extracted from chat or form input."""
    user_id: int
    doctor_name: Optional[str] = None
    specialty: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    time: Optional[str] = None  # HH:MM


class AlternativeSlot(BaseModel):
    """A suggested alternative appointment slot when the requested one is unavailable."""
    slot_id: int
    doctor_id: int
    doctor_name: str
    facility_name: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    channeling_fee: float


class BookingConfirmation(BaseModel):
    """Confirmation details after a successful booking."""
    appointment_id: int
    slot_id: int
    doctor_name: str
    facility_name: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    channeling_fee: float


class BookingResponse(BaseModel):
    """Final response from the booking agent."""
    status: Literal["booked", "alternatives", "not_found", "needs_info"]
    confirmation: Optional[BookingConfirmation] = None
    alternatives: list[AlternativeSlot] = Field(default_factory=list)
    message: str
