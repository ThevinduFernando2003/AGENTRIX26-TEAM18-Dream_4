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
from ...i18n.translate import t, translate_dynamic
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
    none_label = t("panel.report.none", lang)
    with st.expander(t("panel.report.title", lang), expanded=expanded):
        st.caption(t("panel.report.caption", lang))

        samples = _list_sample_reports()
        sample_choice = st.selectbox(
            t("panel.report.pick_sample", lang),
            [none_label] + [p.name for p in samples],
            key="rr_sample",
        )

        uploaded = st.file_uploader(
            t("panel.report.upload", lang), type=["txt"], key="rr_upload"
        )

        pasted = st.text_area(
            t("panel.report.paste", lang),
            value="",
            height=140,
            key="rr_paste",
            placeholder=t("panel.report.paste_ph", lang),
        )

        if st.button(t("panel.report.run", lang), type="primary", key="rr_run"):
            text = ""
            source = ""
            if sample_choice and sample_choice != none_label:
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
                st.warning(t("panel.report.need_input", lang))
            else:
                conn = get_conn()
                cur = conn.execute(
                    "INSERT INTO MedicalReport(user_id, file_url, ocr_text) VALUES(?,?,?)",
                    (user["user_id"], source, text),
                )
                conn.commit()
                report_id = cur.lastrowid

                with st.spinner(t("panel.report.spin_specialists", lang)):
                    opinions = specialist_panel.run_panel(text, report_id)
                with st.spinner(t("panel.report.spin_moderator", lang)):
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
            st.markdown(
                "### " + t("panel.report.opinions_header", lang, id=str(last["report_id"]))
            )
            cols = st.columns(3)
            labels = {
                "cardiology": t("panel.report.lbl_cardiology", lang),
                "internal_medicine": t("panel.report.lbl_internal", lang),
                "radiology": t("panel.report.lbl_radiology", lang),
            }
            conf_label = t("panel.report.confidence", lang)
            flags_label = t("panel.report.flags", lang)
            for col, op in zip(cols, last["opinions"]):
                with col:
                    st.markdown(f"**{labels.get(op['specialist_type'], op['specialist_type'])}**")
                    st.progress(op["confidence"], text=f"{conf_label} {op['confidence']:.2f}")
                    st.markdown(translate_dynamic(op["findings"], lang))
                    if op.get("flags"):
                        st.caption(flags_label + ": " + ", ".join(f"`{f}`" for f in op["flags"]))

            st.markdown("### " + t("panel.report.consensus_header", lang))
            cons = last["consensus"]
            st.markdown(
                f"**{t('panel.report.summary', lang)}** "
                + translate_dynamic(cons["summary"], lang)
            )

            ca, cd = st.columns(2)
            with ca:
                st.markdown("**" + t("panel.report.agreement", lang) + "**")
                for p in cons["points_of_agreement"]:
                    st.markdown(f"- {translate_dynamic(p, lang)}")
            with cd:
                st.markdown("**" + t("panel.report.disagreement", lang) + "**")
                disagreement = cons["points_of_disagreement"]
                # Highlight in warning colour when there IS disagreement.
                no_disag = (
                    len(disagreement) == 1
                    and "no material disagreement" in disagreement[0].lower()
                )
                if no_disag:
                    st.info(translate_dynamic(disagreement[0], lang))
                else:
                    for p in disagreement:
                        st.warning(translate_dynamic(p, lang))

            st.caption(cons["disclaimer"])

        st.markdown(disclaimer(lang))
