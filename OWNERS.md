# Ownership

Lightweight code-ownership map for Team Dream_4. The named owner is the
default reviewer for changes in their paths and the person to ping when
that area breaks. Not a hard lock — anyone can edit anywhere — but
PRs/commits touching someone else's files should loop them in.

## Chanupa

- `project/ui/auth.py` — login / signup / logout / session lifecycle
- `project/ui/panels/emergency.py` — when the `ui/panels/` split lands
- `project/ui/panels/report.py` — when the `ui/panels/` split lands
- `project/db/**` — schema, connection helper, seed loader, seed JSONs
- `project/agents/specialist_panel.py` — 3 independent specialists
- `project/agents/moderator.py` — synthesis + disagreement guard
- `project/notifications/**` — ntfy.sh client + NotificationLog
- `pyproject.toml` — lint/format/build config
- `project/requirements.txt` — dependency pins

## Thevindu, Nisal, Janidu

To be claimed by the respective owners. Suggested split based on
existing module boundaries:

- **Agents / orchestration** — `project/agents/basic_chatbot.py`,
  `project/agents/booking_agent.py`,
  `project/agents/medicine_tracker.py`,
  `project/agents/reminders.py`,
  `project/agents/vision_ocr.py`,
  `project/agents/emergency.py`.
- **UI / Streamlit** — `project/ui/app.py` plus the eventual
  `project/ui/panels/{booking,medicine,prescription,reminders}.py`
  modules.
- **i18n / voice** — `project/i18n/{translate,tts,stt}.py`,
  `project/kb/sample_reports/**`.

Open a PR or edit this file when claims are finalised.

## Rules of thumb

1. Touching someone else's owned path? Tag them in the PR description.
2. Cross-cutting changes (e.g. a new field in `project/models/`) — both
   the owner of `models/` and every downstream owner gets pinged.
3. `OWNERS.md` itself is no-owner — any teammate can update it.
