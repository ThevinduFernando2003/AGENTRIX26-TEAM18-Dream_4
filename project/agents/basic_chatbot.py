"""Basic Agent Chatbot — CrewAI orchestrator with persistent memory.

Per the brief:
1. Persist user message to ChatMessage.
2. Run rule-based emergency screen() BEFORE any LLM call.
3. Load last ~10 ChatMessage rows for this user as conversation memory.
4. Single CrewAI Task classifies intent + drafts reply (JSON output).
5. Persist assistant reply.
6. Return (reply, route, emergency).

The disclaimer is appended in the UI layer, not by the LLM, so it can
never be omitted by a wonky generation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date as dtdate
from datetime import timedelta

from ..db.db import get_conn
from ..i18n.translate import translate_dynamic
from ..models import EmergencyDecision, RouterOutput
from ..rag import retrieve
from . import emergency

logger = logging.getLogger("medbridge.chatbot")

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


# ---------- persistence helpers ----------


def persist_message(user_id: int, role: str, content: str) -> None:
    """Append a chat turn to ChatMessage. Public entry point used by UI panels."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO ChatMessage(user_id, role, content) VALUES(?,?,?)",
        (user_id, role, content),
    )
    conn.commit()


# Back-compat alias for existing internal callers.
_persist_message = persist_message


def load_history(user_id: int, limit: int = 10) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT role, content, timestamp FROM ChatMessage
           WHERE user_id = ? ORDER BY message_id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def _format_transcript(history: list[dict]) -> str:
    if not history:
        return "(no prior messages)"
    lines = []
    for h in history:
        speaker = "Patient" if h["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {h['content']}")
    return "\n".join(lines)


# ---------- CrewAI call ----------

_SYSTEM = (
    "You are MedBridge AI's orchestrator for a multi-agent healthcare navigator "
    "serving patients in Sri Lanka. You NEVER provide a medical diagnosis. You "
    "classify the patient's latest message into exactly one route: "
    "'booking' (they want to schedule a doctor), "
    "'medicine' (they want medicine prices/availability), "
    "'report_review' (they want a medical report reviewed — Tier 2), or "
    "'general' (chat, triage questions, follow-ups). "
    "Produce ONLY a JSON object — no prose around it — matching this schema:\n"
    "{\n"
    '  "route": "booking" | "medicine" | "report_review" | "general",\n'
    '  "reply": "<short, kind reply to the patient>",\n'
    '  "extracted": { ...optional fields like doctor_name, specialty, date, time, medicines: [..] }\n'
    "}\n"
    "Rules:\n"
    "- For booking: try to extract doctor_name, specialty, date (YYYY-MM-DD or 'tomorrow'), time (HH:MM).\n"
    "- For medicine: extract medicines as a list of names.\n"
    "- For report_review: route is 'report_review'; reply briefly says the feature is coming and offer to help otherwise.\n"
    "- Never invent doctors, slots, drugs, dosages, or prices. The specialised agents handle those lookups.\n"
    "- Keep replies to 1-3 sentences. Be warm but factual."
)


@dataclass
class ChatResult:
    reply: str
    route: str
    extracted: dict
    emergency: EmergencyDecision | None = None


# Hard wall-clock budget for the router LLM call. On a throttled key the request
# fails fast to the heuristic instead of hanging the chat.
_LLM_TIMEOUT_S = 8


def _run_llm(user_text: str, transcript: str) -> dict | None:
    """Classify intent + draft a reply with a single direct Gemini JSON call.

    Replaces the former CrewAI Agent/Task/Crew router. That orchestration added
    ~5s per message and, on a rate-limited key, litellm retried 429s with backoff
    into 30-60s hangs (the perceived "stuck"). One direct call with a hard timeout
    and NO retries fails fast to the heuristic, so the UI never freezes. Returns
    None on any failure (missing key, timeout, parse error) → caller uses heuristic.
    """
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    prompt = (
        _SYSTEM
        + "\n\n--- Conversation so far ---\n"
        + transcript
        + "\n\n--- New patient message ---\n"
        + user_text
        + "\n\nReturn ONLY the JSON object."
    )
    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(_GEMINI_MODEL)
        resp = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
            request_options={"timeout": _LLM_TIMEOUT_S},
        )
        raw = (getattr(resp, "text", "") or "").strip()
        return _extract_json(raw)
    except Exception as exc:
        logger.warning("LLM router call failed (%s) — using heuristic", exc)
        return None


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw: str) -> dict | None:
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


# ---------- offline / fallback router ----------


def _heuristic_route(text: str) -> dict:
    """Used when the LLM isn't available — keyword routing so the demo still moves."""
    t = text.lower()
    if any(k in t for k in ("book", "appointment", "channel", "see dr", "see doctor", "consult")):
        return {"route": "booking", "reply": "Let me find an appointment for you.", "extracted": {}}
    if any(k in t for k in ("medicine", "tablet", "pill", "pharmacy", "price")):
        return {
            "route": "medicine",
            "reply": "I'll check pharmacy prices for you.",
            "extracted": {},
        }
    if any(
        k in t
        for k in (
            "report",
            "scan",
            "x-ray",
            "xray",
            "ecg",
            "echo",
            "blood test",
            "lab result",
            "mri",
            "ct scan",
            "ultrasound",
            "review my",
            "second opinion",
        )
    ):
        return {
            "route": "report_review",
            "reply": (
                "I'll open the Specialist Panel. Upload the report text or pick "
                "a sample, and three independent specialists will weigh in."
            ),
            "extracted": {},
        }
    return {
        "route": "general",
        "reply": "I'm here to help. Could you tell me a bit more about what you're experiencing?",
        "extracted": {},
    }


# ---------- RAG grounding (symptom → specialty navigation) ----------

# Minimum cosine similarity before we trust a retrieved specialty. The curated
# notes are short and asymmetric to a patient's phrasing, so scores run modest;
# 0.2 cleanly separates on-topic symptom text from unrelated chatter in testing.
_SPECIALTY_MIN_SCORE = 0.2


def ground_specialty(text: str) -> str | None:
    """Map a free-text symptom description to a specialty via the RAG index.

    This is navigation, NOT diagnosis — it answers "which kind of doctor", never
    "what disease". Returns the specialty name, or None when nothing is confidently
    relevant or the index isn't available (offline-safe: retrieve() returns []).
    """
    hits = retrieve(text, "symptoms", k=3)
    if not hits:
        return None
    top = hits[0]
    if top["score"] < _SPECIALTY_MIN_SCORE:
        return None
    specialty = (top.get("metadata") or {}).get("specialty")
    return specialty or None


# ---------- future-visit reminder detection (Tier 3) ----------

_REM_PATTERNS = [
    # come back / follow up / see me again — in N units
    re.compile(
        r"\b(?:come back|follow[- ]?up|see (?:me|you|the doctor) again|return)\s+(?:in\s+)?(\d+)\s*(day|days|week|weeks|month|months)\b",
        re.IGNORECASE,
    ),
    # come back / follow up — in (a|one|two) month/week
    re.compile(
        r"\b(?:come back|follow[- ]?up|return)\s+(?:in\s+)?(a|an|one|two|three|four|six)\s+(day|week|month)s?\b",
        re.IGNORECASE,
    ),
    # explicit ISO date
    re.compile(r"\b(?:on|by)\s+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE),
    # "next month" / "next week"
    re.compile(
        r"\b(?:come back|follow[- ]?up|see (?:me|you|the doctor) again|return).{0,40}\bnext\s+(week|month)\b",
        re.IGNORECASE,
    ),
]

_WORD_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "six": 6}


def _has_booking_intent(text: str) -> bool:
    """Check if text contains booking verbs/intents.

    Returns True if the user is explicitly trying to book or schedule,
    preventing false-positive reminder detection for phrases like
    'book me in 2 weeks' from being routed to reminders instead of booking.
    """
    booking_keywords = [r"\b(?:book|appointment|schedule|slot|reserve|doctor|consult|specialist)\b"]
    text_lower = text.lower()
    return any(re.search(kw, text_lower) for kw in booking_keywords)


def detect_reminder(text: str, today: dtdate | None = None) -> str | None:
    """Return target_date_or_month string (YYYY-MM-DD or YYYY-MM) if matched.

    Note: This is called BEFORE routing to booking. If the text contains
    booking verbs, we skip reminder detection to avoid the collision
    (e.g., 'book me in 2 weeks' should go to booking, not reminders).
    That check is done by the caller.
    """
    today = today or dtdate.today()
    s = text.strip()

    # Pattern 1: numeric N units
    m = _REM_PATTERNS[0].search(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        return _offset_to_target(today, n, unit)

    # Pattern 2: word-number units
    m = _REM_PATTERNS[1].search(s)
    if m:
        n = _WORD_NUMS.get(m.group(1).lower(), 1)
        unit = m.group(2).lower()
        return _offset_to_target(today, n, unit)

    # Pattern 3: ISO date
    m = _REM_PATTERNS[2].search(s)
    if m:
        try:
            return dtdate.fromisoformat(m.group(1)).isoformat()
        except ValueError:
            pass

    # Pattern 4: "next week/month"
    m = _REM_PATTERNS[3].search(s)
    if m:
        unit = m.group(1).lower()
        return _offset_to_target(today, 1, unit)

    return None


def _offset_to_target(today: dtdate, n: int, unit: str) -> str:
    if unit.startswith("day"):
        return (today + timedelta(days=n)).isoformat()
    if unit.startswith("week"):
        return (today + timedelta(weeks=n)).isoformat()
    if unit.startswith("month"):
        # Naive month offset: add n*30 days for simplicity, then return YYYY-MM.
        target = today + timedelta(days=30 * n)
        return target.strftime("%Y-%m")
    return today.isoformat()


def _persist_reminder(user_id: int, target: str, source_text: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO FutureVisitReminder(user_id, doctor_id, target_date_or_month, notified)
           VALUES(?, NULL, ?, 0)""",
        (user_id, target),
    )
    conn.commit()
    return cur.lastrowid


# ---------- public entry point ----------


def handle(user_id: int, user_text: str, preferred_language: str = "en") -> ChatResult:
    user_text = (user_text or "").strip()
    if not user_text:
        return ChatResult(reply="(empty message)", route="general", extracted={})

    _persist_message(user_id, "user", user_text)

    decision = emergency.screen(user_text)
    if decision.is_emergency:
        # Don't persist a canned assistant reply here — the UI renders the
        # emergency panel and persists the assistant message after the user
        # confirms or dismisses.
        return ChatResult(
            reply="",
            route="emergency",
            extracted={"matched_terms": decision.matched_terms},
            emergency=decision,
        )

    # Tier-3: rule-based reminder detection before the LLM call.
    # IMPORTANT: Skip reminder detection if user has booking intent
    # to avoid collision (e.g., 'book me in 2 weeks' should route to booking, not reminders).
    target = None
    if not _has_booking_intent(user_text):
        target = detect_reminder(user_text)

    if target is not None:
        rid = _persist_reminder(user_id, target, user_text)
        reply_en = (
            f"Got it — I've saved a reminder for around {target}. "
            f"Use 'Check my reminders' in the sidebar when you'd like to be pinged."
        )
        reply = (
            translate_dynamic(reply_en, preferred_language)
            if preferred_language != "en"
            else reply_en
        )
        _persist_message(user_id, "assistant", reply)
        return ChatResult(
            reply=reply,
            route="reminder",
            extracted={"reminder_id": rid, "target": target},
        )

    history = load_history(user_id, limit=10)
    transcript = _format_transcript(history[:-1])  # exclude the message we just inserted

    # Heuristic-first routing: classify cheaply, and only spend an LLM call when the
    # intent is genuinely ambiguous. Unambiguous domain intents (booking/medicine/
    # report verbs) skip the LLM entirely — this is what removes the multi-second
    # hang and, on a rate-limited key, guarantees the chat never blocks. The LLM is
    # reserved for the "general" bucket, where a thoughtful triage reply matters.
    heuristic = _heuristic_route(user_text)
    if heuristic["route"] != "general":
        parsed = heuristic
    else:
        parsed = _run_llm(user_text, transcript) or heuristic
    try:
        out = RouterOutput(**parsed)
    except Exception:
        out = RouterOutput(
            route="general", reply=parsed.get("reply", "How can I help?"), extracted={}
        )

    # RAG grounding: surface the right specialty from the curated index so we never
    # invent one. For triage chat we add a gentle navigation suggestion to the reply;
    # for booking we hand the grounded specialty to the booking agent via `extracted`.
    if out.route in ("general", "booking"):
        grounded = ground_specialty(user_text)
        if grounded:
            out.extracted.setdefault("specialty", grounded)
            if out.route == "general":
                out.reply = (
                    out.reply.rstrip()
                    + f" Based on what you describe, a {grounded} doctor may be the most "
                    "appropriate to see — I can help you book one if you'd like."
                )

    # Tier-3: translate the assistant reply if user prefers Si/Ta.
    final_reply = out.reply
    if preferred_language != "en" and final_reply:
        final_reply = translate_dynamic(final_reply, preferred_language)

    _persist_message(user_id, "assistant", final_reply)
    return ChatResult(reply=final_reply, route=out.route, extracted=out.extracted)
