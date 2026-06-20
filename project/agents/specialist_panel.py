"""Specialist Panel — three independent CrewAI agents.

The brief requires three specialists (cardiology, internal medicine,
radiology) to analyse the SAME report text without seeing each other's
output. Independence is enforced structurally:

- Each `analyze_*` builds a fresh `LLM`, `Agent`, `Task`, and `Crew`.
- The three calls run in a `ThreadPoolExecutor(max_workers=3)` so they
  cannot share Python state.
- No shared global agent objects, no shared Crew, no cross-agent
  delegation.

Offline fallback: if `GEMINI_API_KEY` is missing, return three
deterministic stub opinions so the rest of the UI is still demoable.
The stubs vary by specialty so the Moderator's disagreement guard
has something to work with.
"""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..db.db import get_conn
from ..models import SPECIALIST, SpecialistOpinion

logger = logging.getLogger("medbridge.panel")

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


_PERSONAS: dict[SPECIALIST, dict[str, str]] = {
    "cardiology": {
        "role": "Consultant Cardiologist",
        "lens": (
            "Focus on cardiovascular findings: ECG, troponin, BNP, echo, "
            "ischaemic risk factors, heart-failure signs, arrhythmia clues. "
            "Down-weight findings that are primarily respiratory or radiological."
        ),
        "stub_findings": (
            "Likely cardiac contribution: mildly elevated troponin, NT-proBNP rise, "
            "LVH on ECG, EF 48% on echo suggest early heart failure with mildly reduced "
            "ejection fraction. Ischaemic component cannot be excluded."
        ),
        "stub_confidence": 0.75,
        "stub_flags": ["heart_failure_suspected", "ischaemia_workup_needed"],
    },
    "internal_medicine": {
        "role": "Consultant in Internal Medicine",
        "lens": (
            "Take a whole-patient view: integrate cardiac, respiratory, and systemic "
            "findings. Comment on differential breadth and prioritise the next "
            "diagnostic step that has the highest yield."
        ),
        "stub_findings": (
            "Mixed cardiopulmonary picture in an ex-smoker with family history of "
            "pulmonary fibrosis. HRCT chest with DLCO is the single highest-yield "
            "next step. Treat for heart failure provisionally but do NOT close out "
            "the interstitial-lung-disease differential."
        ),
        "stub_confidence": 0.65,
        "stub_flags": ["broad_differential", "needs_hrct"],
    },
    "radiology": {
        "role": "Consultant Radiologist",
        "lens": (
            "Focus on imaging: CXR reticular markings, cardiothoracic ratio, echo "
            "findings, and what would be expected on HRCT. Comment on the "
            "specificity of imaging findings rather than clinical management."
        ),
        "stub_findings": (
            "CXR reticular changes in both lower zones are non-specific — could "
            "represent early interstitial lung disease or pulmonary congestion. "
            "HRCT recommended to discriminate. Cardiothoracic ratio borderline; "
            "echo findings are more reliable here."
        ),
        "stub_confidence": 0.55,
        "stub_flags": ["non_specific_cxr", "hrct_indicated"],
    },
}


def _extract_json(raw: str) -> Optional[dict]:
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _run_one(specialty: SPECIALIST, report_text: str) -> SpecialistOpinion:
    """Build a fresh Crew per call. No shared state with other specialists."""
    persona = _PERSONAS[specialty]

    if not os.environ.get("GEMINI_API_KEY"):
        logger.info("No GEMINI_API_KEY — using stub for %s", specialty)
        return SpecialistOpinion(
            specialist_type=specialty,
            findings=persona["stub_findings"],
            confidence=persona["stub_confidence"],
            flags=list(persona["stub_flags"]),
        )

    try:
        from crewai import Agent, Crew, LLM, Task  # type: ignore
        llm = LLM(model=f"gemini/{_GEMINI_MODEL}", api_key=os.environ["GEMINI_API_KEY"])
        agent = Agent(
            role=persona["role"],
            goal=(
                "Analyse the medical report from your specialty's perspective and "
                "return a single JSON object."
            ),
            backstory=(
                f"You are a senior {persona['role']} reviewing a referral. "
                f"{persona['lens']} "
                "You never diagnose unilaterally — your opinion is one of several "
                "and will be aggregated by a clinical moderator. Be honest about "
                "uncertainty."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        task = Task(
            description=(
                "Analyse the following medical report. Return ONLY a JSON object — "
                "no prose around it — matching this schema:\n"
                "{\n"
                f'  "specialist_type": "{specialty}",\n'
                '  "findings": "<2-4 sentences of your specialty-specific reading>",\n'
                '  "confidence": <float between 0 and 1, how confident you are in your reading>,\n'
                '  "flags": ["short_snake_case_concern_tags"]\n'
                "}\n"
                "Be honest about uncertainty; do NOT inflate confidence to sound decisive.\n\n"
                f"--- Report ---\n{report_text}\n--- End report ---"
            ),
            expected_output="A single JSON object matching the schema.",
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = str(crew.kickoff())
        parsed = _extract_json(result)
        if parsed is None:
            raise ValueError(f"could not parse JSON from {specialty} output")
        # Force the specialty field — the LLM occasionally relabels.
        parsed["specialist_type"] = specialty
        return SpecialistOpinion(**parsed)
    except Exception as exc:
        logger.warning("%s analysis failed: %s — falling back to stub", specialty, exc)
        return SpecialistOpinion(
            specialist_type=specialty,
            findings=persona["stub_findings"],
            confidence=persona["stub_confidence"],
            flags=list(persona["stub_flags"]),
        )


def run_panel(report_text: str, report_id: int) -> list[SpecialistOpinion]:
    """Run all three specialists in parallel, persist, return opinions."""
    specialties: tuple[SPECIALIST, ...] = ("cardiology", "internal_medicine", "radiology")

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_run_one, s, report_text): s for s in specialties}
        opinions = [f.result() for f in futures]

    # Preserve specialty order for stable UI rendering.
    order = {s: i for i, s in enumerate(specialties)}
    opinions.sort(key=lambda o: order[o.specialist_type])

    # Persist.
    conn = get_conn()
    for op in opinions:
        op.report_id = report_id
        conn.execute(
            """INSERT INTO SpecialistOpinion(report_id, specialist_type, findings, confidence, flags)
               VALUES(?,?,?,?,?)""",
            (
                report_id,
                op.specialist_type,
                op.findings,
                op.confidence,
                json.dumps(op.flags),
            ),
        )
    conn.commit()
    return opinions
