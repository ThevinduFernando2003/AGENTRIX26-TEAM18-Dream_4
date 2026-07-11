# MedBridge AI — Updated Demo Steps (OpenAI live)

**Status:** OpenAI `gpt-4o-mini` is configured and verified · booking table fix is live  
**Patient app:** http://localhost:8501  
**Supplier portal:** http://localhost:8502  
**Time:** ~10–12 minutes  
**Full narration script:** [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md)

---

## Before you start (1 minute)

1. Hard-refresh the browser: **Ctrl+F5**
2. Confirm both URLs load (8501 + 8502)
3. Optional: open the ntfy topic from the sidebar on your phone after login
4. Keep this page / cheat-sheet open

**If either app is down**, in PowerShell from the repo root:

```powershell
cd d:\Dev\Competitions\Agentrix\MedBridge-AI
project\venv\Scripts\Activate.ps1
streamlit run project\ui\app.py
# new terminal:
streamlit run project\ui\supplier_portal.py --server.port 8502
```

---

## Step 1 — Open & login

1. Go to **http://localhost:8501**
2. Login: **`demo1`** / **`demo1pass`**
3. Sidebar → set city to **Colombo** (if shown)

**Expect:** Chat empty state with quick-start hints.

---

## Step 2 — Prove the API key (LLM live)

**Type exactly:**

```text
hello
```

**Expect:** A warm, natural reply (not a short offline stub).  
**This confirms OpenAI is working.**

---

## Step 3 — Emergency screener

**Type exactly:**

```text
I have severe chest pain and can't breathe
```

1. Red emergency panel appears  
2. Click **Confirm**  
3. Show the **`tel:1990`** link  
4. Optional: check phone for ntfy family alert  

**Expect:** No long LLM wait — regex fires first.

---

## Step 4 — Booking (availability table)

**Type exactly:**

```text
Book me with Dr. Sunil Perera tomorrow at 10:00
```

**Expect (updated behavior):**
1. Booking panel appears **above** the chat  
2. Short status message (available / alternatives)  
3. **Table** of slots: Doctor · Facility · Date · Time · Fee  
4. Rows underneath with a **Book** button each  

**Do:**
1. Click **Book** on one row  
2. Wait for the **green success card** (doctor, date, time)  
3. Optional: ntfy booking confirmation on phone  

---

## Step 5 — Medicine price comparison

**Type exactly:**

```text
I need prices for Panadol and Amoxicillin
```

**Expect:** Pharmacy comparison table with LKR totals, distance, stock / “Has all?” badges. Complete baskets ranked first.

---

## Step 6 — Supplier portal (two-sided platform)

1. Open **http://localhost:8502**  
2. Pharmacy tab → select **Union Chemists**  
3. Find **Losartan** → toggle **in stock** → save / publish  
4. Switch back to the patient app (**8501**)  
5. **Type exactly:**

```text
price of Losartan
```

**Expect:** Union Chemists appears (or shows in-stock) — live write into the same DB.

---

## Step 7 — Specialist panel + moderator

**Type exactly:**

```text
Can you review my medical report?
```

1. Open the report panel  
2. Choose sample: **`report_ambiguous_findings.txt`**  
   (path: `project/kb/sample_reports/report_ambiguous_findings.txt`)  
3. Run the 3-specialist panel  

**Expect:** Three opinions + moderator consensus with a **non-empty disagreement** list. May take ~20–40s (OpenAI).

---

## Step 8 — Prescription OCR (confirm gate)

1. Open the prescription / Rx flow  
2. Upload: **`project/kb/sample_prescriptions/sample_rx_en.png`**  
3. **Step 1** — upload  
4. **Step 2** — edit / **confirm** the OCR text  
5. **Step 3** — pharmacy comparison runs only after confirm  

**Expect:** No pharmacy lookup until you confirm.

---

## Step 9 — Sinhala + reminder

1. **Logout**  
2. Login: **`demo3`** / **`demo3pass`** (Sinhala UI)  
3. Send one short message (optional)  
4. **Type exactly:**

```text
come back in 2 weeks
```

5. Sidebar → **Reminders** → fire / show due → check ntfy push  

---

## Close

> “Turn the API key off and this demo still runs on deterministic fallbacks. Structural safety — we don’t trust the LLM to be safe; we make safety structural.”

---

## Copy-paste prompt list

| # | Prompt / action |
|---|---|
| 1 | `hello` |
| 2 | `I have severe chest pain and can't breathe` |
| 3 | `Book me with Dr. Sunil Perera tomorrow at 10:00` → **Book** a row |
| 4 | `I need prices for Panadol and Amoxicillin` |
| 5 | Portal: Losartan in-stock @ Union Chemists → `price of Losartan` |
| 6 | `Can you review my medical report?` → ambiguous sample |
| 7 | Upload `sample_rx_en.png` → confirm → pharmacies |
| 8 | `demo3` / `demo3pass` → `come back in 2 weeks` |

---

## Quick troubleshooting

| Issue | Fix |
|---|---|
| Stub / offline-sounding chat | Confirm `.env` has `LLM_PROVIDER=openai` + key; restart Streamlit; Ctrl+F5 |
| No booking table | Use the exact booking prompt above; refresh; restart patient app |
| Slow specialist panel | Normal on free/paid OpenAI; wait or narrate while it runs |
| Portal 8502 down | Start supplier portal command above |
| ntfy silent | Open sidebar topic URL on phone; continue demo |

**Logins:** `demo1`/`demo1pass` (EN) · `demo3`/`demo3pass` (SI) · `demo4`/`demo4pass` (TA)
