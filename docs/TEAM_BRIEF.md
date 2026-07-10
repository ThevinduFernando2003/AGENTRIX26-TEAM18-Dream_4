# Team brief — send this to Thevindu, Nisal, Chanupa TODAY (Friday)

Copy-paste the message below into the team group, attach `MedBridge_Viva_Guide.md`
and `docs/DEFENSE.md`, and chase anyone who hasn't replied ✅ by tonight.

---

Machang, viva is **tomorrow (Saturday) morning** — all four of us are on the call.
Evaluators review the **frozen hackathon repo** and will ask each of us to defend
our own part ("prove it's your code"). Here's the prep, ~2 hours max:

**Everyone (1 hour):**
1. Read the Viva Guide **Part 1** (shared foundation — what happens when a message
   is sent, the stack, the safety model) and **§1.11** (doc-vs-code drift — know
   these before an examiner finds them) and **Part 4** (gotcha Q&A).
2. Read **DEFENSE.md** (attached) — especially §2–3 (why our own DB instead of
   third-party APIs — the two-sided platform answer) and §5 (security/PDPA).
   These are the questions they reportedly push on.

**Your own vertical (1 hour) — be ready to walk your files line-by-line:**
- **Thevindu** → Guide Part 3-B: booking agent (Pydantic AI typed tools, atomic
  book(), the ±7-day alternatives, the RunContext import bug story, the
  reminder-vs-booking collision fix).
- **Nisal** → Guide Part 3-C: medicine matching ("semantic recall, edit-distance
  precision" guard), OCR confirm gate, dosage-verbatim rule, i18n design.
- **Chanupa** → Guide Part 3-D: auth (bcrypt, session isolation, the honest
  ?uid= limitation), 17-table schema + idempotent seed, specialist panel
  independence (fresh Crew per call, 3 threads), moderator disagreement guard,
  ntfy audit log.

**Demo (I drive, you narrate your part when it's on screen):**
1. Emergency chest-pain → 1990 + family push (me)
2. Book Dr. Sunil Perera tomorrow 10:00 → alternatives → book → push (**Thevindu narrates**)
3. Panadol + Amoxicillin price comparison (**Nisal narrates**)
4. Report upload → 3-specialist panel → moderator disagreements (**Chanupa narrates**)
5. Prescription photo → OCR → confirm gate → comparison (**Nisal narrates**)
6. Sinhala/Tamil turn + voice + reminder push (me)

One line we all say the same way if asked why the demo looks more polished than
the frozen repo: *"The frozen repo is our untouched 12-hour state; rule 4 lets us
keep working in a separate repo — architecture is identical, changes are polish."*

Reply ✅ when you've read your sections. Call me with anything shaky — better
tonight than in front of the panel.
