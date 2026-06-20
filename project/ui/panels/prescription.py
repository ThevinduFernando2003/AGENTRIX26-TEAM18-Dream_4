"""Prescription OCR panel (Tier 2): Gemini Vision transcribe → confirm gate → pharmacy search.

Owner: Nisal. We never search any pharmacy until the user confirms the transcription,
and dosage text is kept verbatim.

Three entry points, all funnelling through the SAME confirm gate so the
"no pharmacy lookup before the user confirms" rule holds for every path:
- a built-in sample image (demo without a live photo),
- uploading your own photo,
- pasting prescription text (works with no GEMINI_API_KEY).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..common import disclaimer, get_geo, lang_of
from ...agents import medicine_tracker, vision_ocr
from ...i18n.translate import t
from ...notifications.ntfy_client import send as ntfy_send, topic_for_user

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "kb" / "sample_prescriptions"
_SAMPLE_IMG = _SAMPLE_DIR / "sample_rx_en.png"
_SAMPLE_TXT = _SAMPLE_DIR / "sample_rx_en.txt"


def _sample_text() -> str:
    try:
        return _SAMPLE_TXT.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _open_confirm_gate(prescription_id: int, ocr_text: str) -> None:
    st.session_state["pending_rx"] = {"prescription_id": prescription_id, "ocr_text": ocr_text}


def render(user: dict) -> None:
    lang = lang_of(user)
    lat, lng = get_geo()
    with st.expander(t("panel.rx.expander", lang), expanded=False):
        st.caption(t("panel.rx.caption", lang))

        if not vision_ocr.is_available():
            st.warning(t("panel.rx.unavailable", lang))

        # --- Sample prescription (lets the OCR flow be demoed without a live photo) ---
        use_sample = st.checkbox(t("panel.rx.use_sample", lang), key="rx_use_sample")
        if use_sample:
            st.caption(t("panel.rx.sample_label", lang))
            if _SAMPLE_IMG.exists():
                st.image(str(_SAMPLE_IMG), use_container_width=True)
            if st.button(t("panel.rx.transcribe", lang), key="rx_ocr_sample"):
                sample_bytes = _SAMPLE_IMG.read_bytes() if _SAMPLE_IMG.exists() else b""
                with st.spinner(t("panel.rx.spinner", lang)):
                    ocr = medicine_tracker.process_prescription(
                        user_id=user["user_id"],
                        image_bytes=sample_bytes,
                        mime_type="image/png",
                    )
                # Offline OCR returns "" → pre-fill the confirm gate with the known
                # sample transcription so the confirm→pharmacy demo still works.
                _open_confirm_gate(ocr.prescription_id, ocr.ocr_text or _sample_text())
                st.rerun()
        else:
            # --- Upload your own photo ---
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
                _open_confirm_gate(ocr.prescription_id, ocr.ocr_text)
                st.rerun()

            # --- Paste fallback (no key needed; still goes through the confirm gate) ---
            pasted = st.text_area(
                t("panel.rx.paste_label", lang),
                placeholder=t("panel.rx.paste_ph", lang),
                key="rx_paste",
            )
            if pasted.strip() and st.button(t("panel.rx.paste_btn", lang), key="rx_paste_btn"):
                conf = medicine_tracker.start_prescription_from_text(user["user_id"], pasted)
                _open_confirm_gate(conf.prescription_id, conf.ocr_text)
                st.rerun()

        # --- Shared confirm gate: the ONLY place that triggers a pharmacy lookup ---
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
