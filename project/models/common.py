"""Shared Literal types used across multiple model modules."""

from __future__ import annotations

from typing import Literal

INTENT = Literal["booking", "medicine", "report_review", "emergency", "general"]
SPECIALIST = Literal["cardiology", "internal_medicine", "radiology"]
