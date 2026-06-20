# RAG subsystem

MedBridge AI grounds three things in a curated knowledge base instead of letting
the LLM free-associate: **symptom → specialty** navigation, **doctor/facility**
resolution, and **medicine-name** resolution. The index is a local, persistent
ChromaDB store; embeddings are local-first so the whole thing works with no API key.

## Pipeline

```
project/kb/*.json + kb/rag_knowledge/*.json
        │  python -m project.rag.ingest
        ▼
  chunk → embed → ChromaDB (persistent, RAG_PERSIST_DIR)
        │
        ▼  project.rag.retrieve(query, collection, k)
  callers: chatbot (symptoms) · booking agent (facilities) · medicine tracker (medicines)
```

## Collections

| Collection | Source | Metadata | Used by |
|---|---|---|---|
| `symptoms` | `kb/rag_knowledge/symptom_specialty.json` | `specialty` | chatbot triage grounding |
| `facilities` | `kb/seed_facilities.json` (specialty descriptions + doctor blurbs) | `specialty`, `facility`, `doctor` | booking agent specialty/doctor resolution |
| `medicines` | `kb/seed_medicines.json` (name + dosage note) | `name` | medicine tracker fuzzy match |

## Embeddings (`project/rag/embeddings.py`)
One factory used by **both** ingest and query so vectors are consistent:
- `GEMINI_API_KEY` set → Gemini `text-embedding-004` (free tier).
- otherwise → ChromaDB's bundled **local ONNX MiniLM** (`onnxruntime`), fully
  offline. Downloaded once (~80 MB) to `~/.cache/chroma`.

## Retrieval contract (`project/rag/retrieve`)
Returns `list[dict]` of `{"text", "metadata", "score"}`, ordered by descending
`score` (`max(0, 1 - cosine_distance)`). The offline / not-yet-ingested / error
path returns `[]` and **never raises**, so every caller keeps a deterministic
fallback (keyword routing, `difflib`, etc.).

## Grounding rules (safety)
- The chatbot maps symptoms to a **specialty**, never a diagnosis or disease name
  (`ground_specialty()` in `basic_chatbot.py`, min-score `0.2`).
- The booking agent resolves fuzzy specialty/doctor text to **real DB rows** — it
  cannot offer a doctor or specialty that isn't in the seed data.
- The medicine tracker maps misspellings/brands to **catalog names only**; dosage
  text is shown verbatim from the catalog and never generated.

## Rebuilding
Re-run `python -m project.rag.ingest` after editing the KB. Ingest is idempotent
(deterministic sha1 ids + `upsert`), so re-runs refresh in place with no duplicate
vectors. The store lives at `RAG_PERSIST_DIR` (default `project/rag/chroma_store/`,
gitignored).
