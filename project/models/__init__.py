"""Models package — back-compat shim.

Re-exports every model so existing
`from project.models import X` / `from ..models import X` imports keep
working unchanged. Add new models to the appropriate submodule
(chat/booking/medicine/panel/common) and extend `__all__` below.
"""

from .booking import (
    AlternativeSlot,
    BookingConfirmation,
    BookingRequest,
    BookingResponse,
)
from .chat import ChatTurn, EmergencyDecision, RouterOutput
from .common import INTENT, SPECIALIST
from .medicine import (
    MedicinePriceItem,
    MedicineQuery,
    MedicineQuoteResult,
    OcrConfirmation,
    PharmacyQuote,
)
from .panel import ConsensusReport, PanelResult, SpecialistOpinion

__all__ = [
    # common
    "INTENT",
    "SPECIALIST",
    # chat
    "ChatTurn",
    "EmergencyDecision",
    "RouterOutput",
    # booking
    "BookingRequest",
    "AlternativeSlot",
    "BookingConfirmation",
    "BookingResponse",
    # medicine
    "MedicineQuery",
    "MedicinePriceItem",
    "PharmacyQuote",
    "MedicineQuoteResult",
    "OcrConfirmation",
    # panel
    "SpecialistOpinion",
    "ConsensusReport",
    "PanelResult",
]
