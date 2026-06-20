"""Build the persistent Chroma index from the hand-built knowledge base.

Run once (and after editing the KB):

    python -m project.rag.ingest

Three collections are produced, each queried by :func:`project.rag.retrieve`:

- ``symptoms``  — curated symptom→specialty navigation notes (triage grounding).
- ``facilities`` — specialty descriptions + doctor/facility blurbs (booking grounding).
- ``medicines`` — catalog medicine names + dosage notes (medicine grounding).

Idempotent: every chunk gets a deterministic id (sha1 of collection+text), so a
re-run ``upsert``s in place instead of creating duplicate vectors. Embeddings come
from :func:`project.rag.embeddings.get_embedding_function` (local ONNX offline,
Gemini ``text-embedding-004`` when ``GEMINI_API_KEY`` is set).
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import chromadb

from .embeddings import RAG_PERSIST_DIR, get_embedding_function, using_gemini

logger = logging.getLogger("medbridge.rag.ingest")

_KB_DIR = Path(__file__).resolve().parent.parent / "kb"
_RAG_KNOWLEDGE_DIR = _KB_DIR / "rag_knowledge"

# Collection names — the public vocabulary callers pass to retrieve(...).
SYMPTOMS = "symptoms"
FACILITIES = "facilities"
MEDICINES = "medicines"
ALL_COLLECTIONS = (SYMPTOMS, FACILITIES, MEDICINES)


def _doc_id(collection: str, text: str) -> str:
    return hashlib.sha1(f"{collection}::{text}".encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- document builders (text + metadata per chunk) ----------

def _symptom_docs() -> list[tuple[str, dict]]:
    docs: list[tuple[str, dict]] = []
    for path in sorted(_RAG_KNOWLEDGE_DIR.glob("*.json")):
        data = _load_json(path)
        for note in data.get("notes", []):
            text = note.get("text", "").strip()
            if text:
                docs.append((text, {"specialty": note.get("specialty", ""), "source": path.name}))
    return docs


def _facility_docs() -> list[tuple[str, dict]]:
    data = _load_json(_KB_DIR / "seed_facilities.json")
    docs: list[tuple[str, dict]] = []
    # Specialty descriptions — the primary booking-grounding signal.
    for sp in data.get("specialties", []):
        text = f"{sp['name']}: {sp.get('description', '')}".strip()
        docs.append((text, {"specialty": sp["name"], "source": "specialties"}))
    # Doctor blurbs — let a fuzzy "heart doctor at Nawaloka" resolve to real rows.
    for fac in data.get("facilities", []):
        for doc in fac.get("doctors", []):
            text = (
                f"{doc['name']} is a {doc['specialty']} doctor at "
                f"{fac['name']} ({fac.get('type', '')}), {fac.get('address', '')}."
            ).strip()
            docs.append(
                (text, {"specialty": doc["specialty"], "facility": fac["name"], "doctor": doc["name"]})
            )
    return docs


def _medicine_docs() -> list[tuple[str, dict]]:
    data = _load_json(_KB_DIR / "seed_medicines.json")
    docs: list[tuple[str, dict]] = []
    for med in data.get("medicines", []):
        name = med["name"]
        # Index the name (so misspellings/brands resolve) plus the dosage note.
        text = f"{name}. {med.get('reference_dosage_text', '')}".strip()
        docs.append((text, {"name": name, "source": "medicines"}))
    return docs


_BUILDERS = {
    SYMPTOMS: _symptom_docs,
    FACILITIES: _facility_docs,
    MEDICINES: _medicine_docs,
}


def ingest() -> dict[str, int]:
    """Build/refresh all collections. Returns {collection: chunk_count}."""
    client = chromadb.PersistentClient(path=RAG_PERSIST_DIR)
    embed_fn = get_embedding_function()
    counts: dict[str, int] = {}

    for name in ALL_COLLECTIONS:
        docs = _BUILDERS[name]()
        # Rebuild in cosine space so `score = 1 - distance` is a real cosine
        # similarity. (Chroma defaults to L2, which makes scores uncomparable.)
        # Delete-then-create keeps re-ingest idempotent with no duplicate vectors.
        try:
            client.delete_collection(name=name)
        except Exception:
            pass
        collection = client.create_collection(
            name=name, embedding_function=embed_fn, metadata={"hnsw:space": "cosine"}
        )
        if docs:
            collection.upsert(
                ids=[_doc_id(name, text) for text, _ in docs],
                documents=[text for text, _ in docs],
                metadatas=[meta for _, meta in docs],
            )
        counts[name] = len(docs)
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    backend = "Gemini text-embedding-004" if using_gemini() else "local ONNX (offline)"
    logger.info("[medbridge.rag] Ingesting KB with %s embeddings → %s", backend, RAG_PERSIST_DIR)
    counts = ingest()
    for name, n in counts.items():
        logger.info("[medbridge.rag]   %-10s %d chunks", name, n)
    logger.info("[medbridge.rag] Ingest complete.")


if __name__ == "__main__":
    main()
