"""Prescription OCR panel (Tier 2): Gemini Vision transcribe → confirm gate → pharmacy search.

Owner: Nisal. We never search any pharmacy until the user confirms the transcription,
and dosage text is kept verbatim.
"""

from __future__ import annotations

import streamlit as st

from ..common import disclaimer, get_geo, lang_of
from ...agents import medicine_tracker, vision_ocr
from ...i18n.translate import t
from ...notifications.ntfy_client import send as ntfy_send, topic_for_user


def render(user: dict) -> None:
    lang = lang_of(user)
    lat, lng = get_geo()
    with st.expander(t("panel.rx.expander", lang), expanded=False):
        st.caption(t("panel.rx.caption", lang))

        if not vision_ocr.is_available():
            st.warning(t("panel.rx.unavailable", lang))

        img = st.file_uploader(
            t("panel.rx.upload", lang),
            type=["png", "jpg", "jpeg"],
            key="rx_upload",
        )
        if img is not None and st.button(t("panel.rx.transcribe", lang), key="rx_ocr"):
            mime = img.type or "image/jpeg"
            with st.spinner(t("panel.rx.spinner", lang)):
                ocr = medicine_tracker.process_prescription(
                    user_id=user["user_id"],
                    image_bytes=img.read(),
                    mime_type=mime,
                )
            st.session_state["pending_rx"] = {
                "prescription_id": ocr.prescription_id,
                "ocr_text": ocr.ocr_text,
            }

        pending = st.session_state.get("pending_rx")
        if pending:
            st.markdown(t("panel.rx.confirm_prompt", lang))
            edited = st.text_area(
                t("panel.rx.edit_label", lang),
                value=pending["ocr_text"] or "",
                height=180,
                key="rx_edit",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button(t("panel.rx.confirm_btn", lang), type="primary", key="rx_yes"):
                    result = medicine_tracker.confirm_prescription(
                        prescription_id=pending["prescription_id"],
                        final_text=edited,
                        user_id=user["user_id"],
                        user_lat=lat,
                        user_lng=lng,
                    )
                    ntfy_send(
                        topic=topic_for_user(user["user_id"]),
                        title="MedBridge AI: prescription confirmed",
                        message=(
                            f"Prescription #{pending['prescription_id']} confirmed. "
                            f"Pharmacy comparison ready."
                        ),
                        user_id=user["user_id"],
                        tags=["pill"],
                        notif_type="prescription_confirmed",
                    )
                    st.session_state["pending_medicine"] = {
                        "message": result.message,
                        "matched_names": result.matched_names,
                        "unmatched_names": result.unmatched_names,
                        "quotes": [q.model_dump() for q in result.quotes],
                    }
                    st.session_state.pop("pending_rx", None)
                    st.rerun()
            with c2:
                if st.button(t("panel.rx.discard_btn", lang), key="rx_no"):
                    st.session_state.pop("pending_rx", None)
                    st.rerun()

        st.markdown(disclaimer(lang))
