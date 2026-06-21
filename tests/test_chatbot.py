"""Chatbot routing — heuristic-first classification stays offline (no key hit).

The Step 2 design routes unambiguous booking/medicine/report intents via the
keyword heuristic without ever calling the LLM. These assert that contract.
"""

from __future__ import annotations

import pytest

from project.agents import basic_chatbot as bc


@pytest.mark.parametrize(
    "text,expected",
    [
        ("I want to book an appointment with a cardiologist", "booking"),
        ("what is the price of paracetamol", "medicine"),
        ("please review my x-ray report", "report_review"),
        ("I have a fever and feel tired", "general"),
    ],
)
def test_heuristic_routes_offline(seeded_db, no_api_key, text, expected):
    result = bc.handle(1, text, preferred_language="en")
    assert result.route == expected


def test_emergency_routes_before_llm(seeded_db, no_api_key):
    result = bc.handle(1, "I have crushing chest pain", preferred_language="en")
    assert result.route == "emergency"
    assert result.emergency is not None and result.emergency.is_emergency


def test_general_reply_is_nonempty(seeded_db, no_api_key):
    # The "general" bucket still returns a friendly reply even with no LLM.
    result = bc.handle(1, "I have a fever and feel tired", preferred_language="en")
    assert result.reply.strip()
