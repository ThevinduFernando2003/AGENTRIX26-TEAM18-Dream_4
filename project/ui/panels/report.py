"""Report review panel (Tier 2): three independent specialists + a moderator.

Owner: Chanupa. A routed "report_review" intent just opens this expander; the
actual run happens when the user supplies a report and clicks Run.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..common import disclaimer, lang_of
from ...agents import moderator, specialist_panel
from ...db.db import get_conn
from ...i18n.translate import t
from ...notifications.ntfy_client import send as ntfy_send, topic_for_user

_SAMPLE_REPORTS_DIR = Path(__file__).resolve().parents[2] / "kb" / "sample_reports"


def _list_sample_reports() -> list[Path]:
    if not _SAMPLE_REPORTS_DIR.exists():
        return []
    return sorted(p for p in _SAMPLE_REPORTS_DIR.iterdir() if p.suffix == ".txt")


def render(user: dict) -> None:
    # A routed report_review intent opens the expander on this run.
    req = st.session_state.get("route_request")
    if req and req.get("route") == "report_review":
        st.session_state["open_report_panel"] = True
        st.session_state.pop("route_request", None)

    expanded = st.session_state.pop("open_report_panel", False)
    lang = lang_of(user)
    with st.expander(t("panel.report.title", lang), expanded=expanded):
        st.caption(
            "Three independent specialists (cardiology, internal medicine, "
            "radiology) each read the SAME report without seeing each other's "
            "output. A moderator then surfaces points of agreement and "
            "disagreement. Reports are text-only in this build."
        )

        samples = _list_sample_reports()
        sample_choice = st.selectbox(
            "Pick a sample report (or use upload / paste below)",
            ["— none —"] + [p.name for p in samples],
            key="rr_sample",
        )

        uploaded = st.file_uploader(
            "Or upload a .txt report", type=["txt"], key="rr_upload"
        )

        pasted = st.text_area(
            "Or paste report text directly",
            value="",
            height=140,
            key="rr_paste",
            placeholder="Paste the full report text here…",
        )

        if st.button(t("panel.report.run", lang), type="primary", key="rr_run"):
            text = ""
            source = ""
            if sample_choice and sample_choice != "— none —":
                path = _SAMPLE_REPORTS_DIR / sample_choice
                text = path.read_text(encoding="utf-8")
                source = sample_choice
            elif uploaded is not None:
                text = uploaded.read().decode("utf-8", errors="replace")
                source = uploaded.name
            elif pasted.strip():
                text = pasted.strip()
                source = "pasted"

            if not text:
                st.warning("Provide a report via sample, upload, or paste.")
            else:
                conn = get_conn()
                cur = conn.execute(
                    "INSERT INTO MedicalReport(user_id, file_url, ocr_text) VALUES(?,?,?)",
                    (user["user_id"], source, text),
                )
                conn.commit()
                report_id = cur.lastrowid

                with st.spinner("Three specialists reviewing independently…"):
                    opinions = specialist_panel.run_panel(text, report_id)
                with st.spinner("Moderator synthesising…"):
                    consensus = moderator.synthesize(opinions, report_id)

                ntfy_send(
                    topic=topic_for_user(user["user_id"]),
                    title="MedBridge AI: report review complete",
                    message=(
                        f"Specialist panel review for report #{report_id} ready. "
                        f"{len(consensus.points_of_disagreement)} point(s) of disagreement."
                    ),
                    user_id=user["user_id"],
                    tags=["clipboard"],
                    notif_type="report_review_complete",
                )

                st.session_state["last_panel"] = {
                    "report_id": report_id,
                    "opinions": [o.model_dump() for o in opinions],
                    "consensus": consensus.model_dump(),
                }

        last = st.session_state.get("last_panel")
        if last:
            st.markdown(f"### Specialist opinions — report #{last['report_id']}")
            cols = st.columns(3)
            labels = {
                "cardiology": "🫀 Cardiology",
                "internal_medicine": "🩺 Internal medicine",
                "radiology": "🖼️ Radiology",
            }
            for col, op in zip(cols, last["opinions"]):
                with col:
                    st.markdown(f"**{labels.get(op['specialist_type'], op['specialist_type'])}**")
                    st.progress(op["confidence"], text=f"Confidence {op['confidence']:.2f}")
                    st.markdown(op["findings"])
                    if op.get("flags"):
                        st.caption("Flags: " + ", ".join(f"`{f}`" for f in op["flags"]))

            st.markdown("### Moderator consensus")
            cons = last["consensus"]
            st.markdown(f"**Summary.** {cons['summary']}")

            ca, cd = st.columns(2)
            with ca:
                st.markdown("**Points of agreement**")
                for p in cons["points_of_agreement"]:
                    st.markdown(f"- {p}")
            with cd:
                st.markdown("**Points of disagreement**")
                disagreement = cons["points_of_disagreement"]
                # Highlight in warning colour when there IS disagreement.
                no_disag = (
                    len(disagreement) == 1
                    and "no material disagreement" in disagreement[0].lower()
                )
                if no_disag:
                    st.info(disagreement[0])
                else:
                    for p in disagreement:
                        st.warning(p)

            st.caption(cons["disclaimer"])

        st.markdown(disclaimer(lang))
