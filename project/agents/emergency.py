"""Pure-regex emergency screener.

Runs BEFORE any LLM call on every user message in the chatbot. It must
be cheap, deterministic, and never depend on an external API.

False positives are acceptable here — surfacing the emergency panel
when in doubt is the safe failure mode. The agent always asks the user
to confirm before invoking the tel:1990 link or sending the family
push, so a false positive costs one extra click.
"""

from __future__ import annotations

import re
from typing import Iterable

from ..models import EmergencyDecision

# English + a handful of high-confidence Sinhala/Tamil terms. Lowercased
# for matching; the screener also lowercases the input.
_PATTERNS: list[tuple[str, str]] = [
    # cardiac / respiratory
    (r"\bchest pain\b",                "chest pain"),
    (r"\bcrushing chest\b",            "crushing chest pain"),
    (r"\bcan('?| no)?t breathe\b",     "can't breathe"),
    (r"\bcannot breathe\b",            "cannot breathe"),
    (r"\bshort(ness)? of breath\b",    "shortness of breath"),
    (r"\bgasping\b",                   "gasping for air"),
    # stroke
    (r"\bface (is )?droop(ing)?\b",    "face drooping"),
    (r"\bslurred speech\b",            "slurred speech"),
    (r"\bcan('?| no)?t move (my )?(arm|leg|side)\b", "limb weakness"),
    (r"\bone side (of my )?body (is )?numb\b", "one-sided numbness"),
    # bleeding / trauma
    (r"\bbleeding heavily\b",          "heavy bleeding"),
    (r"\bwon('?| no)?t stop bleeding\b", "uncontrolled bleeding"),
    (r"\bvomiting blood\b",            "vomiting blood"),
    (r"\bcoughing up blood\b",         "coughing up blood"),
    # consciousness
    (r"\bunconscious\b",               "unconscious"),
    (r"\bpassed out\b",                "loss of consciousness"),
    (r"\bnot responding\b",            "unresponsive"),
    (r"\bseizure\b",                   "seizure"),
    (r"\bconvuls(ing|ion)\b",          "convulsion"),
    # allergic / anaphylaxis
    (r"\banaphyla(xis|ctic)\b",        "anaphylaxis"),
    (r"\bthroat (is )?closing\b",      "throat closing"),
    (r"\bsevere allergic reaction\b",  "severe allergic reaction"),
    # infants / pediatric
    (r"\bbaby (is )?not breathing\b",  "baby not breathing"),
    (r"\bchild (is )?unresponsive\b",  "child unresponsive"),
    # self-harm / suicide
    (r"\bsuicid(e|al)\b",              "suicidal ideation"),
    (r"\bkill myself\b",               "self-harm risk"),
    (r"\bhurt myself\b",               "self-harm risk"),
    (r"\bend (my|it) (life|all)\b",    "self-harm risk"),
    # poisoning / overdose
    (r"\boverdose\b",                  "overdose"),
    (r"\bswallowed (poison|bleach|pills)\b", "poison ingestion"),
    # Sinhala (romanised) — common terms users may type without diacritics
    (r"\bhansiya\b",                   "stroke (Sinhala)"),
    # Tamil (romanised)
    (r"\bmaarpu valli\b",              "chest pain (Tamil)"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), label) for pat, label in _PATTERNS]


def screen(text: str) -> EmergencyDecision:
    if not text:
        return EmergencyDecision(is_emergency=False)
    matched: list[str] = []
    for regex, label in _COMPILED:
        if regex.search(text):
            matched.append(label)
    if not matched:
        return EmergencyDecision(is_emergency=False)
    return EmergencyDecision(
        is_emergency=True,
        matched_terms=_dedupe(matched),
        reason=f"Detected: {', '.join(_dedupe(matched))}",
    )


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out
