"""MedBridge AI models package.

This package is split by domain for parallel, non-overlapping development:
- common.py: shared type definitions (INTENT, SPECIALIST, etc.)
- chat.py: chat/routing models (owned by Janidu)
- booking.py: booking models (owned by Thevindu)
- medicine.py: medicine/pharmacy models (owned by Nisal)
- panel.py: specialist panel/report models (owned by Chanupa)

For backward compatibility, all models are re-exported here.
"""

from .chat import ChatTurn, EmergencyDecision, RouterOutput
from .booking import (
    BookingRequest,
    AlternativeSlot,
    BookingConfirmation,
    BookingResponse,
)
from .medicine import (
    MedicineQuery,
    MedicinePriceItem,
    PharmacyQuote,
    MedicineQuoteResult,
)
from .panel import (
    SpecialistOpinion,
    ConsensusReport,
    PanelResult,
    OcrConfirmation,
)
from .common import INTENT, SPECIALIST

__all__ = [
    # Common
    "INTENT",
    "SPECIALIST",
    # Chat
    "ChatTurn",
    "EmergencyDecision",
    "RouterOutput",
    # Booking
    "BookingRequest",
    "AlternativeSlot",
    "BookingConfirmation",
    "BookingResponse",
    # Medicine
    "MedicineQuery",
    "MedicinePriceItem",
    "PharmacyQuote",
    "MedicineQuoteResult",
    # Panel
    "SpecialistOpinion",
    "ConsensusReport",
    "PanelResult",
    "OcrConfirmation",
]
