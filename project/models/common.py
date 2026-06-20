"""Common types shared across all models."""

from typing import Literal

INTENT = Literal["booking", "medicine", "report_review", "emergency", "general"]
SPECIALIST = Literal["cardiology", "internal_medicine", "radiology"]
