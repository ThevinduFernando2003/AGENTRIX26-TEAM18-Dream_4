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
from datetime import date as dtdate, timedelta
from typing import Optional

from ..db.db import get_conn
from ..i18n.translate import translate_dynamic
from ..models import EmergencyDecision, RouterOutput
from . import emergency

logger = logging.getLogger("medbridge.chatbot")

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")


# ---------- persistence helpers ----------

def _persist_message(user_id: int, role: str, content: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO ChatMessage(user_id, role, content) VALUES(?,?,?)",
        (user_id, role, content),
    )
    conn.commit()


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
    emergency: Optional[EmergencyDecision] = None


_crew_agent = None  # lazy init


def _get_agent():
    """Lazy-build the CrewAI agent. Gracefully degrades if CrewAI / API key absent."""
    global _crew_agent
    if _crew_agent is not None:
        return _crew_agent
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    try:
        from crewai import Agent, LLM  # type: ignore
        llm = LLM(model=f"gemini/{_GEMINI_MODEL}", api_key=os.environ["GEMINI_API_KEY"])
        _crew_agent = Agent(
            role="Healthcare Navigator Orchestrator",
            goal=(
                "Triage the patient's message, classify intent, and produce a short "
                "user-facing reply. Never diagnose; never invent clinical facts."
            ),
            backstory=(
                "You coordinate a team of specialist agents (booking, medicine tracker, "
                "report review) and never replace a licensed physician."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        return _crew_agent
    except Exception as exc:
        logger.warning("CrewAI agent unavailable: %s", exc)
        return None


def _run_llm(user_text: str, transcript: str) -> Optional[dict]:
    agent = _get_agent()
    if agent is None:
        return None
    try:
        from crewai import Task, Crew  # type: ignore
        task = Task(
            description=(
                _SYSTEM
                + "\n\n--- Conversation so far ---\n"
                + transcript
                + "\n\n--- New patient message ---\n"
                + user_text
                + "\n\nReturn ONLY the JSON object."
            ),
            expected_output="A single JSON object matching the schema in the instructions.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        raw = str(result)
        return _extract_json(raw)
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return None


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw: str) -> Optional[dict]:
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
        return {"route": "medicine", "reply": "I'll check pharmacy prices for you.", "extracted": {}}
    if any(
        k in t
        for k in (
            "report", "scan", "x-ray", "xray", "ecg", "echo",
            "blood test", "lab result", "mri", "ct scan", "ultrasound",
            "review my", "second opinion",
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


# ---------- future-visit reminder detection (Tier 3) ----------

_REM_PATTERNS = [
    # come back / follow up / see me again — in N units
    re.compile(r"\b(?:come back|follow[- ]?up|see (?:me|you|the doctor) again|return)\s+(?:in\s+)?(\d+)\s*(day|days|week|weeks|month|months)\b", re.IGNORECASE),
    # come back / follow up — in (a|one|two) month/week
    re.compile(r"\b(?:come back|follow[- ]?up|return)\s+(?:in\s+)?(a|an|one|two|three|four|six)\s+(day|week|month)s?\b", re.IGNORECASE),
    # explicit ISO date
    re.compile(r"\b(?:on|by)\s+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE),
    # "next month" / "next week"
    re.compile(r"\b(?:come back|follow[- ]?up|see (?:me|you|the doctor) again|return).{0,40}\bnext\s+(week|month)\b", re.IGNORECASE),
]

_WORD_NUMS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "six": 6}


def detect_reminder(text: str, today: Optional[dtdate] = None) -> Optional[str]:
    """Return target_date_or_month string (YYYY-MM-DD or YYYY-MM) if matched."""
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
    target = detect_reminder(user_text)
    if target is not None:
        rid = _persist_reminder(user_id, target, user_text)
        reply_en = (
            f"Got it — I've saved a reminder for around {target}. "
            f"Use 'Check my reminders' in the sidebar when you'd like to be pinged."
        )
        reply = translate_dynamic(reply_en, preferred_language) if preferred_language != "en" else reply_en
        _persist_message(user_id, "assistant", reply)
        return ChatResult(
            reply=reply,
            route="reminder",
            extracted={"reminder_id": rid, "target": target},
        )

    history = load_history(user_id, limit=10)
    transcript = _format_transcript(history[:-1])  # exclude the message we just inserted

    parsed = _run_llm(user_text, transcript) or _heuristic_route(user_text)
    try:
        out = RouterOutput(**parsed)
    except Exception:
        out = RouterOutput(route="general", reply=parsed.get("reply", "How can I help?"), extracted={})

    # Tier-3: translate the assistant reply if user prefers Si/Ta.
    final_reply = out.reply
    if preferred_language != "en" and final_reply:
        final_reply = translate_dynamic(final_reply, preferred_language)

    _persist_message(user_id, "assistant", final_reply)
    return ChatResult(reply=final_reply, route=out.route, extracted=out.extracted)
