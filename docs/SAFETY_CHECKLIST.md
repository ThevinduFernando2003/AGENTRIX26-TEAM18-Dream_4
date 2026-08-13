# MedBridge AI — Structural Safety Checklist (non-negotiable)

Use in every PR that touches agents, panels, LLM, booking, OCR, emergency, or moderator.

## Must remain true

- [ ] **Emergency before LLM** — `emergency.screen()` runs before any model call on the chat path  
- [ ] **Confirm before dial/push** — emergency UI requires explicit confirm  
- [ ] **OCR confirm gate** — no pharmacy lookup until user confirms transcription  
- [ ] **Dosage** — only catalog `reference_dosage_text`; model never invents dose  
- [ ] **Booking write path** — only `booking_agent.book()` inserts appointments; LLM `status=booked` is downgraded  
- [ ] **Atomic booking** — slot UNIQUE / transaction; no double-book  
- [ ] **Disagreement visible** — moderator `points_of_disagreement` never silently empty  
- [ ] **No diagnosis** — UI disclaimer on clinical surfaces; specialty navigation only  
- [ ] **Fail-soft intelligence** — LLM/RAG failures degrade; app does not crash  
- [ ] **SEED labeling** — catalog demos remain labeled until live suppliers  

## Tests that must stay green

- Emergency pattern tests  
- Booking atomicity / cancel (when added) tests  
- Moderator / panel invariant tests (or stubs offline)  
- OCR/prescription gate behavior (where covered)  
- Full `pytest` suite in CI  

**If a change weakens any box above → do not merge.**
