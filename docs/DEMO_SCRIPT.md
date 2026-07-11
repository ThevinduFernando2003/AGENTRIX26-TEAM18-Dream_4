# MedBridge AI — Live Demo Script (narration)

**Apps:** Patient http://localhost:8501 · Supplier http://localhost:8502  
**Login:** `demo1` / `demo1pass` (later `demo3` / `demo3pass`)  
**LLM:** OpenAI `gpt-4o-mini` via `project/.env`  
**Length:** ~10–12 minutes

---

## Opening (30 seconds)

> “MedBridge AI is a healthcare **navigator**, never a diagnoser. Five agent groups behind one trilingual chat. Safety is structural — emergency screening is pure regex before any LLM, booking writes are atomic SQL, OCR needs human confirmation, and every AI feature has a deterministic fallback.”

*(Hard-refresh the browser if needed: Ctrl+F5.)*

---

## Step 1 — Open & login

**Do:** Open http://localhost:8501 → login `demo1` / `demo1pass` → set city to **Colombo** in the sidebar.

**Say:**  
> “Patient app on 8501. Seeded demo users, bcrypt passwords, Colombo as default location for distance sorting.”

---

## Step 2 — Quick key check

**Type:** `hello`

**Expect:** Warm LLM reply (not a stub).

**Say:**  
> “That reply is live from OpenAI gpt-4o-mini through our provider-agnostic `llm.py` layer — we can flip Gemini or OpenAI with one `.env` line.”

---

## Step 3 — Emergency

**Type:**
```text
I have severe chest pain and can't breathe
```

**Do:** Click **Confirm** → show `tel:1990`.  
*(Optional: phone subscribed to sidebar ntfy URL → family push.)*

**Say:**  
> “Emergency screening is pure regex — about thirty patterns across English and romanised Sinhala/Tamil — and it runs **before** any LLM. Zero latency on the safety path. User must confirm before we dial or push.”

---

## Step 4 — Booking (table of available times)

**Type:**
```text
Book me with Dr. Sunil Perera tomorrow at 10:00
```

**Expect:**
- Booking panel above chat
- Message about availability / alternatives
- **Table** of slots (Doctor, Facility, Date, Time, Fee)
- Row actions with **Book** buttons

**Do:** Click **Book** on one row → green success card.

**Say:**  
> “Chat routes booking heuristically for speed. We enrich doctor, date, and time from the message, then Pydantic AI proposes slots through typed SQL tools. Only deterministic `book()` writes the appointment — atomic transaction, slot UNIQUE. The table is what the patient confirms against.”

---

## Step 5 — Medicine prices

**Type:**
```text
I need prices for Panadol and Amoxicillin
```

**Expect:** Pharmacy comparison table — LKR totals, distance, stock / “Has all?”

**Say:**  
> “Fuzzy plus RAG medicine matching with a precision guard. Complete baskets rank first, then total cost, then distance from the patient’s city.”

---

## Step 6 — Supplier portal (two-sided platform)

**Do:**
1. Open http://localhost:8502  
2. Pharmacy → **Union Chemists** → toggle **Losartan** in-stock → save  
3. Back to patient app → type: `price of Losartan`

**Expect:** Union Chemists appears / shows in stock.

**Say:**  
> “This is the two-sided platform model — same idea as eChannelling or PickMe. Suppliers publish into MedBridge; we fetch nothing. Our database is the system of record. No open Sri Lankan pharmacy API exists, so the platform *is* the integration.”

---

## Step 7 — Specialist panel

**Type:**
```text
Can you review my medical report?
```

**Do:** Pick `report_ambiguous_findings.txt` → run panel.

**Expect:** Three specialist columns + moderator consensus with **non-empty disagreement**.

**Say:**  
> “Three CrewAI specialists in separate threads, no shared state — independence is structural. The moderator’s disagreement list can never be empty; that’s a code invariant, not a prompt hope.”

---

## Step 8 — Prescription OCR

**Do:** Upload `project/kb/sample_prescriptions/sample_rx_en.png`  
→ Step 1 upload → Step 2 edit/confirm → Step 3 pharmacy compare.

**Say:**  
> “Vision OCR runs, but pharmacy lookup never starts until the human confirms. Dosage is only ever shown verbatim from the catalog — we don’t let the model invent doses.”

---

## Step 9 — Sinhala + reminder

**Do:** Logout → login `demo3` / `demo3pass`

**Type:**
```text
come back in 2 weeks
```

**Do:** Sidebar → Reminders → fire / show push.

**Say:**  
> “Full English / Sinhala / Tamil UI, plus voice. Reminders are regex-based, idempotent, and they yield to booking intent so ‘book me in two weeks’ never becomes a reminder by mistake.”

---

## Close (20 seconds)

> “Turn the API key off and this entire demo still runs on deterministic fallbacks. We don’t trust the LLM to be safe — we make safety structural. Happy to take questions.”

---

## Contingencies (if something fails)

| Problem | What to say / do |
|---|---|
| Slow / 429 from OpenAI | “Graceful degradation kicks in — designed behavior.” Use booking/medicine anyway (deterministic SQL). |
| No booking table | Re-type the exact booking line; hard refresh; confirm you’re on the restarted app. |
| ntfy silent | Show sidebar topic URL + History / notification audit. |
| Portal down | Restart `:8502` or narrate the two-sided platform from DEFENSE.md. |
| App crash | Switch to backup recording if you have one. |

---

## Exact prompts cheat-sheet (copy-paste)

1. `hello`  
2. `I have severe chest pain and can't breathe`  
3. `Book me with Dr. Sunil Perera tomorrow at 10:00`  
4. `I need prices for Panadol and Amoxicillin`  
5. `price of Losartan` *(after portal toggle)*  
6. `Can you review my medical report?`  
7. *(upload)* `sample_rx_en.png`  
8. `come back in 2 weeks` *(as demo3)*
