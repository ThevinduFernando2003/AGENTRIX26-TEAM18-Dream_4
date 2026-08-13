# MedBridge AI — Software Architecture Document (SAD)

**Project:** MedBridge AI · AgenTrix 2026 · Team Dream_4 (TEAM18)  
**Version:** 1.1  
**Status:** Living document — as-built architecture + target production architecture  
**Related:** [`SRS.md`](SRS.md) · [`architecture.md`](architecture.md) · [`UPGRADE_PLAN.md`](UPGRADE_PLAN.md) · [`DEFENSE.md`](DEFENSE.md)

---

## 1. Introduction

### 1.1 Purpose

This SAD describes the software architecture of MedBridge AI: major components, connectors, data stores, external dependencies, and the intended evolution path.

### 1.2 Scope

Covers the **as-built Streamlit prototype** and the **target production** architecture. Detailed Mermaid diagrams live in [`architecture.md`](architecture.md).

### 1.3 Architectural goals

1. Structural safety over prompt trust  
2. Graceful degradation without API keys  
3. Parallel team development via panel contract  
4. Two-sided platform data model (suppliers publish in)  
5. Presentation swappable without rewriting agents  

---

## 2. Architectural drivers

| Driver | Response |
|---|---|
| No open SL channeling/pharmacy APIs | Own marketplace tables; supplier publish seam |
| 12-hour hackathon / free tier | Streamlit + SQLite + local embeddings |
| Multi-agent demo credibility | CrewAI panel; Pydantic AI booking; heuristic chat router |
| Safety | Regex emergency first; OCR confirm; atomic book; disagreement guard |
| Offline demos | Deterministic fallbacks; `retrieve()` never raises |

---

## 3. As-built architecture (current)

### 3.1 Six-layer view

```
CLIENT        Browser · Family ntfy subscriber · tel:1990 dialer
PRESENTATION  Streamlit app.py + panels (:8501)
              Supplier portal concept (:8502)
AGENTS        chatbot · emergency · booking · medicine ·
              specialist_panel · moderator · OCR · reminders
INTELLIGENCE  llm.py (Gemini|OpenAI) · RAG retriever
DATA          SQLite (17 tables) · ChromaDB · kb/ seed JSON
EXTERNAL      LLM APIs · ntfy.sh · gTTS
```

Diagram source: `docs/architecture.md` (also `architecture.html`, PNGs).

### 3.2 Component catalog

| Component | Path | Responsibility |
|---|---|---|
| Patient shell | `project/ui/app.py` | Bootstrap, auth gate, panel orchestration |
| Supplier portal | `project/ui/supplier_portal.py` | Concept publish of prices/slots |
| Panels | `project/ui/panels/*` | Domain UI; `render(user)` contract |
| Chat router | `project/agents/basic_chatbot.py` | Persist, emergency, heuristic/LLM route, RAG ground |
| Emergency | `project/agents/emergency.py` | Pure regex screener |
| Booking | `project/agents/booking_agent.py` | Enrich, tools, atomic book |
| Medicine | `project/agents/medicine_tracker.py` | Match + quote + sort |
| Specialist panel | `project/agents/specialist_panel.py` | 3 parallel CrewAI agents |
| Moderator | `project/agents/moderator.py` | Consensus + disagreement invariant |
| LLM façade | `project/llm.py` | Provider switch; fail-soft |
| RAG | `project/rag/*` | Embed, ingest, retrieve |
| DB | `project/db/*` | Schema, seed, connections |
| Models | `project/models.py` | Pydantic contracts |
| i18n / voice | `project/i18n/*` | Catalog, STT, TTS |
| Notifications | `project/notifications/ntfy_client.py` | Push + audit log |

### 3.3 Key connectors

| Connector | Mechanism |
|---|---|
| Chat → domain panels | `st.session_state["route_request"]` one-shot signal |
| Panel → agent | Direct Python import inside owning panel |
| Agent → DB | `get_conn()` + SQL tools |
| Agent → LLM | `project.llm` helpers only |
| Agent → RAG | `retrieve(query, collection, k)` |
| Agent → family | `ntfy_client.send` → `NotificationLog` |

### 3.4 Chat-turn lifecycle

```
User message
 → persist ChatMessage
 → emergency.screen()          # no LLM
 → reminder detect (if not booking)
 → heuristic route OR llm.generate_json()
 → ground_specialty() via RAG
 → translate if si/ta
 → domain route_request → panel → agent → SQLite/ntfy
```

### 3.5 Data architecture

- **SQLite** file: `project/db/app.db` (gitignored)  
- **17 tables** — see SRS §6 / `schema.sql`  
- **Chroma** persistent store for vectors; local ONNX embeddings by default  
- **Seed JSON** under `project/kb/` labeled SEED DATA — not live  

### 3.6 Deployment (as-built)

| Process | Command | Port |
|---|---|---|
| Patient app | `streamlit run project/ui/app.py` | 8501 |
| Supplier portal | `streamlit run project/ui/supplier_portal.py --server.port 8502` | 8502 |

Optional: Streamlit Community Cloud via `st.secrets` bridge in `app.py`.

### 3.7 Design patterns

1. **Thin shell / fat panels** — `app.py` has no domain logic  
2. **Heuristic-first routing** — booking/medicine/report skip LLM when clear  
3. **Propose vs commit** — LLM may propose slots; only `book()` writes  
4. **Fail-soft intelligence** — empty string / `[]` / deterministic path on errors  
5. **Panel ownership** — four developers, one vertical each  

---

## 4. Target architecture (production)

```
Patient PWA / React     Hospital Admin SPA     Pharmacy Merchant SPA
            \                 |                    /
             \                |                   /
              v               v                  v
                 API Gateway (TLS, JWT, rate limit)
                              |
                         FastAPI backend
          +---------------+---+---------------+
          |               |                   |
     Agent workers   Booking/Catalog      Notify service
     (queue)         services             (FCM/SMS/WhatsApp)
          |               |                   |
          +-------+-------+---------+---------+
                  v                 v
            Postgres (+ object store for Rx images)
            Vector index (pgvector / managed)
                  |
            Observability · Consent · Audit
```

**Migration rule:** preserve agent/tool contracts; replace presentation, auth, and datastore first. See `docs/DEFENSE.md`.

---

## 5. Security & privacy architecture

| Concern | As-built | Target |
|---|---|---|
| Passwords | bcrypt | bcrypt/argon2 + lockout |
| Sessions | Streamlit + unsigned `?uid=` | Signed cookie / JWT |
| Authorization | Single patient role | RBAC: patient, hospital, pharmacy, admin |
| Transport | Local HTTP | TLS everywhere |
| Data at rest | SQLite unencrypted | Postgres + encryption |
| Push | Guessable ntfy topics | Authenticated FCM/SMS |
| Audit | `NotificationLog` | Full admin audit + consent log |
| Compliance | Disclaimers + scoping | PDPA consent, export, delete |

---

## 6. Quality attributes & tactics

| Attribute | Tactic |
|---|---|
| Safety | Regex-before-LLM; confirm gates; moderator invariants; UI disclaimers |
| Availability | Deterministic fallbacks; local embeddings |
| Performance | Heuristic routes; 8s LLM timeouts; no retry storms |
| Modifiability | Panel contract; `llm.py` façade; typed models |
| Testability | 52 offline pytest tests; seed fixtures |

---

## 7. Team ownership (as-built)

| Owner | Components |
|---|---|
| Janidu | Chatbot, emergency, RAG, `app.py`, chat/sidebar/history |
| Thevindu | Booking agent, reminders, booking panel |
| Nisal | Medicine, prescription OCR, i18n |
| Chanupa | Auth, DB, specialist panel, moderator, notifications, report panel |

---

## 8. Architecture decisions (ADRs summary)

| Decision | Rationale |
|---|---|
| Streamlit UI | Fast pure-Python demo; panel parallelization |
| SQLite | Zero-ops ACID booking for prototype |
| Heuristic-first chat routing | Avoid CrewAI latency/429 hangs on chat path |
| CrewAI for specialist panel only | Role/task abstraction + parallel independence |
| Pydantic AI for booking | Typed tools prevent invented slots |
| Local ONNX RAG | Offline, free, stable dimensions |
| Own catalog tables | No open APIs; two-sided platform model |
| ntfy.sh | Free push for demo; audit logged |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Streamlit/SQLite scale limits | Phase 2 FastAPI + Postgres |
| Supplier cold start | Free portals + anchor chain/hospital pilot |
| LLM quota/cost | Heuristic-first; caching; provider switch |
| Doc/code drift | SRS/SAD/UPGRADE_PLAN as living docs; CI |
| Scope creep into diagnosis | Explicit non-goals in SRS |

---

## 10. Traceability

| Artifact | Location |
|---|---|
| Detailed diagrams | `docs/architecture.md` |
| Requirements | `docs/SRS.md` |
| Upgrade phases | `docs/UPGRADE_PLAN.md` |
| Defense answers | `docs/DEFENSE.md` |
| Code map | `docs/CODEBASE_EXPLANATION.md` |
