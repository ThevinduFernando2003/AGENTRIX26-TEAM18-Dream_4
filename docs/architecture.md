# MedBridge AI — System Architecture

Two diagrams: the **six-layer system view** and the **lifecycle of one chat turn**.
Renders in VS Code (Mermaid extension) and on GitHub. A browser-viewable copy is
[architecture.html](architecture.html); export: `npx -y @mermaid-js/mermaid-cli -i docs/architecture.md -o docs/architecture.png`.

## 1. Six-layer system view

```mermaid
flowchart TB
    subgraph CLIENT["CLIENT"]
        direction LR
        BROWSER["Patient browser"]
        FAMILY["Family phone<br/>ntfy subscriber"]
        DIALER["Phone dialer<br/>tel:1990"]
    end

    subgraph PRESENTATION["PRESENTATION — Streamlit (project/ui)"]
        direction LR
        APP["app.py<br/>thin shell + auth gate"]
        PANELS["9 panels: sidebar · chat · emergency ·<br/>booking · medicine · report · prescription · history"]
    end

    subgraph AGENTS["AGENT LAYER (project/agents)"]
        direction LR
        ROUTER["Chat router<br/>heuristic-first"]
        EMERG["Emergency screener<br/>pure regex — no LLM"]
        BOOK["Booking agent<br/>Pydantic AI + typed SQL tools"]
        MED["Medicine tracker<br/>fuzzy + RAG match"]
        PANEL3["Specialist panel<br/>3 independent CrewAI agents"]
        MODER["Moderator<br/>disagreement guard"]
        OCR["Vision OCR<br/>confirm gate"]
        REMIND["Reminders<br/>regex + push"]
    end

    subgraph INTEL["INTELLIGENCE LAYER"]
        direction LR
        LLMSW["project/llm.py<br/>LLM_PROVIDER switch"]
        RAGR["RAG retriever<br/>offline-safe, never raises"]
    end

    subgraph DATA["DATA LAYER"]
        direction LR
        SQLITE[("SQLite — 17 tables<br/>users · bookings · prescriptions · audit")]
        CHROMA[("ChromaDB<br/>local ONNX embeddings")]
        KB["kb/ seed JSON<br/>labeled SEED DATA — not live"]
    end

    subgraph EXT["EXTERNAL (free tier)"]
        direction LR
        LLMAPI["LLM API<br/>Gemini 2.5 Flash / OpenAI"]
        NTFY["ntfy.sh push"]
        GTTS["gTTS voice out"]
    end

    %% Invisible node-level links pin the layer stacking (Client top → External bottom).
    DIALER ~~~ APP
    PANELS ~~~ EMERG
    RAGR ~~~ KB
    CHROMA ~~~ LLMAPI
    SQLITE ~~~ NTFY

    BROWSER --> APP --> PANELS
    PANELS -- "route_request signal" --> AGENTS
    ROUTER & BOOK & PANEL3 & MODER & OCR --> LLMSW --> LLMAPI
    ROUTER & BOOK & MED --> RAGR --> CHROMA
    AGENTS --> SQLITE
    KB -- "idempotent seed + ingest" --> SQLITE & CHROMA
    EMERG -.->|"no LLM, no network"| DIALER
    REMIND & PANELS --> NTFY --> FAMILY
    PANELS --> GTTS
```

**Layer responsibilities**

| Layer | Responsibility |
|---|---|
| Client | Browser UI, family ntfy subscriber, emergency dialer |
| Presentation | Thin shell + panels; panels talk only via `st.session_state` signals (`route_request`) |
| Agent | Domain logic, typed Pydantic contracts, deterministic offline fallback per agent |
| Intelligence | One provider layer for every LLM call (`LLM_PROVIDER`); RAG retrieval grounding |
| Data | SQLite system-of-record + Chroma vectors + labeled seed catalog |
| External | Free-tier LLM API, push notifications, TTS |

## 2. One chat turn (request lifecycle)

```mermaid
flowchart TD
    A["User message"] --> B["emergency.screen()<br/>pure regex — BEFORE any LLM"]
    B -->|emergency| C["Red panel → confirm →<br/>tel:1990 + family ntfy push"]
    B -->|clear| D{"booking intent?"}
    D -->|no| E["detect_reminder() regex"]
    E -->|matched| F["Persist reminder →<br/>sidebar push later"]
    D -->|yes| G["Heuristic route"]
    E -->|no match| G
    G -->|"booking / medicine / report verbs"| I["Skip LLM — instant route"]
    G -->|ambiguous| H["ONE direct LLM JSON call<br/>8 s timeout, no retries"]
    H -->|fail| I
    H -->|ok| I
    I --> J["RAG grounding:<br/>symptom → specialty (never disease)"]
    J --> K["route_request signal →<br/>domain panel runs its agent"]
    K --> L["Agent → SQLite / RAG / push<br/>reply translated si/ta · disclaimer by UI code"]
```

**Three principles to say out loud while pointing at this:**
1. **Emergency first** — the safety path is 32 compiled regexes, ~32 µs per message, synchronous, zero network, zero API cost (~100,000× cheaper than the LLM call it guards — that's why it runs on every message).
2. **Heuristic before LLM** — unambiguous intents never wait on a model; the LLM is reserved for genuinely ambiguous turns and fails fast to the heuristic.
3. **Structural safety** — disclaimers, confirm gates, and atomic booking are enforced by code, not by prompts.
