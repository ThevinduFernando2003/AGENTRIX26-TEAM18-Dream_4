"""Emergency screener — deterministic regex, no API. True positives + clean negatives."""

from __future__ import annotations

import pytest

from project.agents import emergency


@pytest.mark.parametrize(
    "text",
    [
        "I have crushing chest pain",
        "I can't breathe",
        "help, I feel suicidal",
        "he is unconscious on the floor",
        "she is having a seizure",
        "I am vomiting blood",
    ],
)
def test_true_positives(text):
    assert emergency.screen(text).is_emergency, text


@pytest.mark.parametrize(
    "text",
    [
        "I have a mild headache",
        "just a runny nose since yesterday",
        "can you help me book a doctor",
        "",
    ],
)
def test_clean_negatives(text):
    assert not emergency.screen(text).is_emergency, text


def test_matched_terms_and_reason_populated():
    decision = emergency.screen("crushing chest pain and I can't breathe")
    assert decision.is_emergency
    assert decision.matched_terms  # at least one label
    assert decision.reason and "Detected" in decision.reason
