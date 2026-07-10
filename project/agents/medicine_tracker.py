"""Medicine Tracker Agent — text-input pharmacy price/distance comparison.

NEVER invents dosage. Only displays dosage exactly as stored in the
Medicine table (seeded from a hand-built JSON). Tier 2 will add OCR
with explicit user confirmation before any pharmacy lookup runs.
"""

from __future__ import annotations

import difflib
import logging
import math
import re
from dataclasses import dataclass

from ..db.db import get_conn
from ..models import (
    MedicinePriceItem,
    MedicineQuoteResult,
    OcrConfirmation,
    PharmacyQuote,
)
from ..rag import retrieve
from . import vision_ocr

logger = logging.getLogger("medbridge.medicine")

# RAG resolution thresholds. A small embedding model rates *any* drug-like token as
# similar to *every* catalog drug, so cosine score alone gives false positives
# (e.g. "aspirin"→"Atorvastatin"). We require BOTH a minimum cosine score AND a
# character-level closeness to the resolved name's primary token, so only genuine
# spelling variants ("parasetmol"→"Paracetamol") pass — semantic recall, edit-distance precision.
_MED_RAG_MIN_SCORE = 0.3
_MED_NAME_CHAR_RATIO = 0.6


def _rag_resolve_medicine(raw: str) -> str | None:
    """Resolve a misspelled name to a catalog name via the RAG index.

    Offline-safe: retrieve() returns [] without an index, so this returns None and
    the caller keeps the existing substring/difflib behaviour.
    """
    hits = retrieve(raw, "medicines", k=1)
    if not hits or hits[0]["score"] < _MED_RAG_MIN_SCORE:
        return None
    name = (hits[0].get("metadata") or {}).get("name")
    if not name:
        return None
    # Precision guard: reject semantically-similar but different drugs and nonsense.
    primary = name.split()[0].lower()
    if difflib.SequenceMatcher(None, raw.strip().lower(), primary).ratio() < _MED_NAME_CHAR_RATIO:
        return None
    return name


def _all_medicine_names() -> list[tuple[int, str]]:
    conn = get_conn()
    rows = conn.execute("SELECT medicine_id, name FROM Medicine").fetchall()
    return [(r["medicine_id"], r["name"]) for r in rows]


def match_medicines(names: list[str]) -> tuple[list[int], list[str], list[str]]:
    """Return (medicine_ids, matched_display_names, unmatched_inputs)."""
    catalog = _all_medicine_names()
    lower_catalog = [(mid, n, n.lower()) for mid, n in catalog]

    matched_ids: list[int] = []
    matched_names: list[str] = []
    unmatched: list[str] = []
    seen_ids: set[int] = set()

    for raw in names:
        q = raw.strip().lower()
        if not q:
            continue
        hit = next(((mid, n) for mid, n, ln in lower_catalog if q in ln or ln in q), None)
        if not hit:
            close = difflib.get_close_matches(
                q, [ln for _, _, ln in lower_catalog], n=1, cutoff=0.7
            )
            if close:
                ln = close[0]
                hit = next(((mid, n) for mid, n, x in lower_catalog if x == ln), None)
        if not hit:
            # RAG fallback: vector-match misspellings/brands difflib missed.
            rag_name = _rag_resolve_medicine(raw)
            if rag_name:
                hit = next(((mid, n) for mid, n, _ in lower_catalog if n == rag_name), None)
        if hit and hit[0] not in seen_ids:
            matched_ids.append(hit[0])
            matched_names.append(hit[1])
            seen_ids.add(hit[0])
        elif not hit:
            unmatched.append(raw.strip())
    return matched_ids, matched_names, unmatched


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def quotes_for(medicine_ids: list[int]) -> list[PharmacyQuote]:
    """Build a per-pharmacy quote: items in stock, total cost, missing list."""
    if not medicine_ids:
        return []
    conn = get_conn()
    placeholders = ",".join("?" * len(medicine_ids))
    rows = conn.execute(
        f"""SELECT p.pharmacy_id, p.name AS pharmacy_name, p.address, p.lat, p.lng,
                   m.medicine_id, m.name AS medicine_name,
                   pmp.price, pmp.in_stock
            FROM Pharmacy p
            JOIN PharmacyMedicinePrice pmp ON pmp.pharmacy_id = p.pharmacy_id
            JOIN Medicine m ON m.medicine_id = pmp.medicine_id
            WHERE pmp.medicine_id IN ({placeholders})""",
        medicine_ids,
    ).fetchall()

    grouped: dict[int, dict] = {}
    for r in rows:
        ph = grouped.setdefault(
            r["pharmacy_id"],
            {
                "pharmacy_id": r["pharmacy_id"],
                "pharmacy_name": r["pharmacy_name"],
                "address": r["address"],
                "lat": r["lat"],
                "lng": r["lng"],
                "items": [],
                "missing_ids": set(medicine_ids),
            },
        )
        if r["in_stock"]:
            ph["items"].append(
                MedicinePriceItem(
                    medicine_id=r["medicine_id"],
                    name=r["medicine_name"],
                    price=float(r["price"]),
                )
            )
            ph["missing_ids"].discard(r["medicine_id"])

    # Resolve missing medicine_ids to names for display.
    name_lookup = {mid: name for mid, name in _all_medicine_names()}

    quotes: list[PharmacyQuote] = []
    for ph in grouped.values():
        if not ph["items"]:
            continue
        missing = sorted(name_lookup.get(mid, f"#{mid}") for mid in ph["missing_ids"])
        quotes.append(
            PharmacyQuote(
                pharmacy_id=ph["pharmacy_id"],
                pharmacy_name=ph["pharmacy_name"],
                address=ph["address"],
                items=ph["items"],
                total_cost=round(sum(i.price for i in ph["items"]), 2),
                missing=missing,
            )
        )
    return quotes


def dosage_for(medicine_ids: list[int]) -> dict[int, str]:
    if not medicine_ids:
        return {}
    conn = get_conn()
    placeholders = ",".join("?" * len(medicine_ids))
    rows = conn.execute(
        f"SELECT medicine_id, reference_dosage_text FROM Medicine WHERE medicine_id IN ({placeholders})",
        medicine_ids,
    ).fetchall()
    return {r["medicine_id"]: r["reference_dosage_text"] or "" for r in rows}


# ---------- orchestrator ----------


@dataclass
class MedicineContext:
    user_id: int
    raw_text: str
    extracted_names: list[str] | None = None
    user_lat: float | None = None
    user_lng: float | None = None


_SPLIT_RE = re.compile(r"[,\n;]| and ", re.IGNORECASE)


def _names_from_text(raw: str) -> list[str]:
    """Best-effort medicine name extraction from a free-form chat message.

    Two passes: (1) scan the seeded catalog and pick up any name that
    appears as a substring (handles space-separated lists like
    'paracetamol metformin losartan'); (2) fall back to delimiter
    splitting so non-catalog tokens still go to the fuzzy matcher.
    """
    text = raw.lower()
    hits: list[str] = []
    seen: set[str] = set()
    for _, name in _all_medicine_names():
        # Match on the leading word(s) of the catalog name so
        # 'paracetamol' matches 'Paracetamol 500mg'.
        primary = name.split()[0].lower()
        if primary and primary in text and name not in seen:
            hits.append(name)
            seen.add(name)
    if hits:
        return hits

    cleaned = re.sub(
        r"(?i)\b(price[s]? of|how much|cost of|need|i want|i'?d like|find me|"
        r"check|please|prices?|for|the|i|me|my)\b",
        " ",
        raw,
    )
    parts = [p.strip() for p in _SPLIT_RE.split(cleaned) if p.strip() and len(p.strip()) > 2]
    return parts


def process(ctx: MedicineContext) -> MedicineQuoteResult:
    names = ctx.extracted_names or _names_from_text(ctx.raw_text)
    if not names:
        return MedicineQuoteResult(
            status="no_match",
            message="Tell me which medicine(s) you need — e.g. 'Panadol 500mg and Amoxicillin 500mg'.",
        )

    matched_ids, matched_names, unmatched = match_medicines(names)
    if not matched_ids:
        return MedicineQuoteResult(
            status="no_match",
            unmatched_names=unmatched,
            message=(
                "I couldn't match those to our (demo) medicine list. Try a more specific name "
                "such as 'Paracetamol 500mg'."
            ),
        )

    quotes = quotes_for(matched_ids)
    if not quotes:
        return MedicineQuoteResult(
            status="no_match",
            matched_names=matched_names,
            unmatched_names=unmatched,
            message="No pharmacy in our (demo) list currently stocks any of those.",
        )

    if ctx.user_lat is None or ctx.user_lng is None:
        # Complete baskets first, then lowest cost — a pharmacy missing an item must
        # never outrank a complete one just because its partial total is lower.
        quotes.sort(key=lambda q: (len(q.missing), q.total_cost))
        return MedicineQuoteResult(
            status="no_location",
            matched_names=matched_names,
            unmatched_names=unmatched,
            quotes=quotes,
            message=(
                "Showing pharmacies with the complete list first, sorted by total cost. "
                "Pick a city (or allow location) in the sidebar to also rank by distance."
            ),
        )

    # Attach distances.
    conn = get_conn()
    coords = {
        r["pharmacy_id"]: (r["lat"], r["lng"])
        for r in conn.execute("SELECT pharmacy_id, lat, lng FROM Pharmacy").fetchall()
    }
    for q in quotes:
        lat, lng = coords.get(q.pharmacy_id, (None, None))
        if lat is not None and lng is not None:
            q.distance_km = round(haversine_km(ctx.user_lat, ctx.user_lng, lat, lng), 2)

    # Composite sort: complete baskets first, then lowest cost, then distance — a
    # pharmacy missing an item must never outrank a complete one on partial total.
    quotes.sort(
        key=lambda q: (
            len(q.missing),
            q.total_cost,
            q.distance_km if q.distance_km is not None else 9999,
        )
    )
    return MedicineQuoteResult(
        status="ok",
        matched_names=matched_names,
        unmatched_names=unmatched,
        quotes=quotes,
        message="Pharmacies stocking the complete list first, sorted by total cost and distance.",
    )


# ---------- prescription OCR flow (Tier 2) ----------


def process_prescription(
    user_id: int,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> OcrConfirmation:
    """Run OCR, persist as unconfirmed, return the extracted text.

    The caller MUST present the returned text back to the user for
    explicit confirmation before calling `confirm_prescription`. No
    pharmacy lookup is performed here.
    """
    ocr_text = vision_ocr.extract_prescription_text(image_bytes, mime_type=mime_type)
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO Prescription(user_id, input_type, ocr_text, user_confirmed)
           VALUES(?,?,?,0)""",
        (user_id, "photo", ocr_text),
    )
    conn.commit()
    return OcrConfirmation(
        prescription_id=cur.lastrowid,
        ocr_text=ocr_text,
        confirmed=False,
    )


def confirm_prescription(
    prescription_id: int,
    final_text: str,
    user_id: int,
    user_lat: float | None = None,
    user_lng: float | None = None,
) -> MedicineQuoteResult:
    """User has approved/edited the OCR text. Persist + run pharmacy search."""
    final_text = (final_text or "").strip()
    conn = get_conn()
    conn.execute(
        "UPDATE Prescription SET ocr_text = ?, user_confirmed = 1 WHERE prescription_id = ?",
        (final_text, prescription_id),
    )
    conn.commit()

    return process(
        MedicineContext(
            user_id=user_id,
            raw_text=final_text,
            user_lat=user_lat,
            user_lng=user_lng,
        )
    )


def start_prescription_from_text(user_id: int, text: str) -> OcrConfirmation:
    """Paste-text entry into the confirm-gate flow (no OCR / no key needed).

    Persists an *unconfirmed* text prescription and returns it so the UI shows the
    same confirm gate as the photo path. No pharmacy lookup runs until the user
    confirms via confirm_prescription() — identical safety contract to OCR.
    """
    text = (text or "").strip()
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO Prescription(user_id, input_type, ocr_text, user_confirmed)
           VALUES(?,?,?,0)""",
        (user_id, "text", text),
    )
    conn.commit()
    return OcrConfirmation(prescription_id=cur.lastrowid, ocr_text=text, confirmed=False)
