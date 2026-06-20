"""UI panels for MedBridge AI.

This package is what makes the repo safe to edit in parallel: each panel lives in
its own module with a single, fixed owner, instead of all sharing one giant
``app.py``. ``app.py`` is now a thin shell that just calls each panel's ``render``.

Panel contract — every module in this package follows it:

    def render(user: dict) -> None:
        ...

  - Takes the logged-in ``user`` dict (from ``project.ui.auth.current_user``).
  - Returns ``None``. It draws straight to the Streamlit page and reads/writes
    ``st.session_state``; it never returns data up to ``app.py``.
  - Shared helpers (geolocation, language, disclaimer) come from
    ``project.ui.common`` — never re-implemented per panel.

Chat-routing contract (decoupled route signal):

  - ``chat.py`` is the only panel that talks to ``basic_chatbot.handle``. When the
    user's intent routes to a domain, it writes a one-shot signal and reruns:

        st.session_state["route_request"] = {
            "route": "booking" | "medicine" | "report_review",
            "extracted": {...},     # structured fields from the router
            "raw_text": "<user message>",
        }

  - Each domain panel, at the top of its ``render``, checks for *its* route, does
    its own agent call, fills its ``pending_*`` state, and pops ``route_request``.
    This keeps ``chat.py`` free of any domain-agent imports, so booking/medicine/
    report logic stays entirely in its owner's file.

Ownership (per PLAN1): chat, emergency, sidebar -> Janidu; booking -> Thevindu;
medicine, prescription -> Nisal; report -> Chanupa.
"""
