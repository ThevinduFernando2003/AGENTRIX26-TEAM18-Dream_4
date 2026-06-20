"""MedBridge AI — Streamlit entry point.

Run with:
    streamlit run project/ui/app.py

Flows wired here:
- Auth gate (login/signup)
- Sidebar: user info, mock-data banner, ntfy topic, location, logout
- Chat: persistent history, calls Basic Agent Chatbot
- Emergency: rule-based detection → confirm → tel:1990 link + ntfy push
- Booking: alternatives list, click-to-confirm + ntfy push
- Medicine: text-input pharmacy comparison table
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# Allow `streamlit run project/ui/app.py` to find the `project` package.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(_ROOT / "project" / ".env")
load_dotenv(_ROOT / ".env")  # fallback

from project.db.db import get_conn, init_db  # noqa: E402
from project.ui.auth import current_user, logout, render_auth_gate  # noqa: E402
from project.agents import (  # noqa: E402
    basic_chatbot,
    booking_agent,
    medicine_tracker,
    moderator,
    specialist_panel,
    vision_ocr,
)
from project.notifications.ntfy_client import send as ntfy_send, topic_for_user  # noqa: E402

DISCLAIMER = (
    "_This is an AI-generated observation, not a medical diagnosis. "
    "Please consult a licensed physician or pharmacist._"
)

_SAMPLE_REPORTS_DIR = _ROOT / "project" / "kb" / "sample_reports"

st.set_page_config(page_title="MedBridge AI", page_icon="🩺", layout="wide")

# Lazy DB init on first run.
if not st.session_state.get("_db_inited"):
    init_db(seed=True)
    st.session_state["_db_inited"] = True


# ---------- helpers ----------

def _get_geo() -> tuple[float | None, float | None]:
    geo = st.session_state.get("geo") or {}
    lat = geo.get("latitude") or geo.get("lat")
    lng = geo.get("longitude") or geo.get("lng")
    manual = st.session_state.get("manual_geo") or {}
    return (lat or manual.get("lat"), lng or manual.get("lng"))


def _render_sidebar(user: dict) -> None:
    with st.sidebar:
        st.markdown(f"### 👤 {user.get('full_name') or user['username']}")
        st.caption(f"Language: {user.get('preferred_language', 'en')}")

        st.warning("Demo build — all facility, doctor, slot, pharmacy and price data is SEED / MOCK data.")

        topic = topic_for_user(user["user_id"])
        st.markdown("**Family-alert push topic**")
        st.code(topic, language="text")
        st.caption(
            f"Family subscribes at https://ntfy.sh/{topic} (free, no signup) to get "
            "emergency notifications."
        )

        st.divider()
        st.markdown("**Your location** (for pharmacy distance)")
        try:
            from streamlit_geolocation import streamlit_geolocation  # type: ignore
            geo_val = streamlit_geolocation()
            if isinstance(geo_val, dict) and geo_val.get("latitude"):
                st.session_state["geo"] = geo_val
        except Exception:
            st.caption("(geolocation component unavailable — use manual entry below)")

        lat, lng = _get_geo()
        if lat is not None and lng is not None:
            st.success(f"📍 {lat:.4f}, {lng:.4f}")
        else:
            st.info("Click the 📍 button above, or enter coordinates manually:")

        with st.expander("Enter coordinates manually"):
            m_lat = st.number_input("Latitude",  value=6.9271, format="%.6f")
            m_lng = st.number_input("Longitude", value=79.8612, format="%.6f")
            if st.button("Use these coordinates"):
                st.session_state["manual_geo"] = {"lat": m_lat, "lng": m_lng}
                st.rerun()

        st.divider()
        if st.button("Log out"):
            logout()
            st.rerun()


# ---------- emergency panel ----------

def _render_emergency_panel(user: dict) -> None:
    em = st.session_state.get("pending_emergency")
    if not em:
        return
    st.error("🚨 **Possible medical emergency detected**")
    st.markdown(f"**Triggered by:** {', '.join(em.get('matched_terms', []))}")
    st.markdown(
        "If you confirm, MedBridge AI will show a tap-to-call link for Sri Lanka emergency "
        "services (**1990 Suwa Seriya**) and send a push notification to your saved family "
        "contact via ntfy.sh."
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, this is an emergency", type="primary", use_container_width=True):
            st.session_state["emergency_confirmed"] = True
            topic = topic_for_user(user["user_id"])
            ok = ntfy_send(
                topic=topic,
                title="MedBridge AI: emergency alert",
                message=(
                    f"{user.get('full_name') or user['username']} flagged a possible emergency: "
                    f"{', '.join(em.get('matched_terms', []))}. They have been directed to dial 1990."
                ),
                user_id=user["user_id"],
                priority="urgent",
                tags=["rotating_light", "ambulance"],
                notif_type="emergency",
            )
            st.session_state["emergency_push_ok"] = ok
            # Persist the assistant turn so chat history reflects what happened.
            from project.agents.basic_chatbot import _persist_message
            _persist_message(
                user["user_id"], "assistant",
                "Emergency flow triggered. Please call 1990 immediately. Your family contact has been notified.",
            )
            st.rerun()
    with c2:
        if st.button("❌ No, false alarm", use_container_width=True):
            st.session_state.pop("pending_emergency", None)
            from project.agents.basic_chatbot import _persist_message
            _persist_message(
                user["user_id"], "assistant",
                "Understood — flagging as a false alarm. Tell me more about how you're feeling.",
            )
            st.rerun()

    if st.session_state.get("emergency_confirmed"):
        st.markdown("---")
        st.link_button(
            "📞  Call 1990 now (Suwa Seriya Ambulance)",
            "tel:1990",
            type="primary",
            use_container_width=True,
        )
        if st.session_state.get("emergency_push_ok"):
            st.success(f"Family contact notified at {datetime.now().strftime('%H:%M:%S')} via ntfy.sh.")
        else:
            st.warning("Family push notification could not be sent (logged regardless). Please call 1990.")
        if st.button("Dismiss and continue chatting"):
            for k in ("pending_emergency", "emergency_confirmed", "emergency_push_ok"):
                st.session_state.pop(k, None)
            st.rerun()

    st.markdown(DISCLAIMER)


# ---------- booking panel ----------

def _render_pending_booking(user: dict) -> None:
    pb = st.session_state.get("pending_booking")
    if not pb:
        return
    st.subheader("Booking suggestions")
    st.write(pb["message"])
    if not pb.get("alternatives"):
        st.info("No available alternatives in the next week. Try another doctor or specialty.")
        if st.button("Dismiss"):
            st.session_state.pop("pending_booking", None)
            st.rerun()
        return

    for alt in pb["alternatives"]:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{alt['doctor_name']}** @ {alt['facility_name']}  \n"
                f"{alt['date']} at {alt['time']} · Fee: LKR {alt['channeling_fee']:.0f}"
            )
        with col2:
            if st.button("Book", key=f"book_{alt['slot_id']}"):
                conf = booking_agent.book(user["user_id"], alt["slot_id"])
                if conf is None:
                    st.warning("That slot was just taken — please pick another.")
                else:
                    topic = topic_for_user(user["user_id"])
                    ntfy_send(
                        topic=topic,
                        title="MedBridge AI: appointment confirmed",
                        message=(
                            f"Appointment #{conf.appointment_id} with {conf.doctor_name} at "
                            f"{conf.facility_name} on {conf.date} {conf.time}."
                        ),
                        user_id=user["user_id"],
                        tags=["calendar"],
                        notif_type="booking_confirmed",
                    )
                    from project.agents.basic_chatbot import _persist_message
                    _persist_message(
                        user["user_id"], "assistant",
                        f"Appointment confirmed: {conf.doctor_name} at {conf.facility_name} on "
                        f"{conf.date} {conf.time}. (Appointment #{conf.appointment_id})",
                    )
                    st.session_state.pop("pending_booking", None)
                    st.success(
                        f"Booked with {conf.doctor_name} on {conf.date} at {conf.time}. "
                        "Push notification sent."
                    )
                    st.rerun()
    if st.button("Dismiss booking suggestions"):
        st.session_state.pop("pending_booking", None)
        st.rerun()
    st.markdown(DISCLAIMER)


# ---------- report review panel (Tier 2) ----------

def _list_sample_reports() -> list[Path]:
    if not _SAMPLE_REPORTS_DIR.exists():
        return []
    return sorted(p for p in _SAMPLE_REPORTS_DIR.iterdir() if p.suffix == ".txt")


def _render_report_review(user: dict) -> None:
    expanded = st.session_state.pop("open_report_panel", False)
    with st.expander("📄 Specialist Panel report review", expanded=expanded):
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

        if st.button("Run Specialist Panel", type="primary", key="rr_run"):
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

        st.markdown(DISCLAIMER)


# ---------- prescription OCR panel (Tier 2) ----------

def _render_prescription_panel(user: dict) -> None:
    lat, lng = _get_geo()
    with st.expander("💊 Prescription photo (OCR + confirm gate)", expanded=False):
        st.caption(
            "Upload a prescription photo. Gemini Vision will transcribe it. "
            "You MUST confirm the transcription is exactly what your "
            "prescription says before we search any pharmacy. We never "
            "invent or modify dosage text."
        )

        if not vision_ocr.is_available():
            st.warning(
                "Gemini Vision is unavailable (no GEMINI_API_KEY). "
                "You can still paste your prescription text below."
            )

        img = st.file_uploader(
            "Upload prescription photo (PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            key="rx_upload",
        )
        if img is not None and st.button("Transcribe with Gemini Vision", key="rx_ocr"):
            mime = img.type or "image/jpeg"
            with st.spinner("Running OCR…"):
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
            st.markdown(
                "**Is this exactly what's written on your prescription?** "
                "Edit the text below if anything is wrong, then confirm."
            )
            edited = st.text_area(
                "Transcribed prescription (editable)",
                value=pending["ocr_text"] or "",
                height=180,
                key="rx_edit",
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Yes — search pharmacies", type="primary", key="rx_yes"):
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
                if st.button("❌ Discard and start over", key="rx_no"):
                    st.session_state.pop("pending_rx", None)
                    st.rerun()

        st.markdown(DISCLAIMER)


# ---------- medicine panel ----------

def _render_pending_medicine() -> None:
    pm = st.session_state.get("pending_medicine")
    if not pm:
        return
    st.subheader("Pharmacy comparison")
    st.write(pm["message"])
    if pm.get("matched_names"):
        st.caption(f"Matched: {', '.join(pm['matched_names'])}")
    if pm.get("unmatched_names"):
        st.caption(f"Not in (demo) catalog: {', '.join(pm['unmatched_names'])}")
    if pm["quotes"]:
        table = []
        for q in pm["quotes"]:
            row = {
                "Pharmacy": q["pharmacy_name"],
                "Address": q.get("address") or "",
                "Items": ", ".join(f"{i['name']} (LKR {i['price']:.0f})" for i in q["items"]),
                "Total (LKR)": f"{q['total_cost']:.0f}",
            }
            if q.get("distance_km") is not None:
                row["Distance (km)"] = f"{q['distance_km']:.2f}"
            if q.get("missing"):
                row["Out of stock"] = ", ".join(q["missing"])
            table.append(row)
        st.dataframe(table, use_container_width=True, hide_index=True)
    if st.button("Dismiss medicine results"):
        st.session_state.pop("pending_medicine", None)
        st.rerun()
    st.markdown(DISCLAIMER)


# ---------- main ----------

def main() -> None:
    user = render_auth_gate()
    if not user:
        return

    _render_sidebar(user)

    st.title("🩺 MedBridge AI")
    st.caption("Multi-agent healthcare navigator — Tier 1 demo (Team Dream_4 · AgenTrix 2026)")

    # Show any active in-progress panels first so they're not buried under chat.
    _render_emergency_panel(user)
    _render_pending_booking(user)
    _render_pending_medicine()
    _render_report_review(user)
    _render_prescription_panel(user)

    # ----- chat history -----
    history = basic_chatbot.load_history(user["user_id"], limit=50)
    for h in history:
        with st.chat_message(h["role"] if h["role"] in ("user", "assistant") else "assistant"):
            st.markdown(h["content"])

    user_text = st.chat_input("Describe your symptoms, or ask to book an appointment or check medicine prices…")
    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        result = basic_chatbot.handle(user["user_id"], user_text)

        if result.route == "emergency":
            st.session_state["pending_emergency"] = {
                "matched_terms": result.emergency.matched_terms if result.emergency else [],
            }
            st.rerun()

        # Render assistant reply.
        if result.reply:
            with st.chat_message("assistant"):
                st.markdown(result.reply)

        if result.route == "booking":
            ctx = booking_agent.BookingContext(user_id=user["user_id"], extracted=result.extracted)
            resp = booking_agent.process(ctx)
            st.session_state["pending_booking"] = {
                "message": resp.message,
                "alternatives": [a.model_dump() for a in resp.alternatives],
            }
            st.rerun()

        elif result.route == "medicine":
            lat, lng = _get_geo()
            ctx = medicine_tracker.MedicineContext(
                user_id=user["user_id"],
                raw_text=user_text,
                extracted_names=result.extracted.get("medicines"),
                user_lat=lat,
                user_lng=lng,
            )
            res = medicine_tracker.process(ctx)
            st.session_state["pending_medicine"] = {
                "message": res.message,
                "matched_names": res.matched_names,
                "unmatched_names": res.unmatched_names,
                "quotes": [q.model_dump() for q in res.quotes],
            }
            st.rerun()

        elif result.route == "report_review":
            st.session_state["open_report_panel"] = True
            st.rerun()

    # Footer disclaimer always visible.
    st.markdown("---")
    st.markdown(DISCLAIMER)


if __name__ == "__main__":
    main()
else:
    # Streamlit imports this as a module on each rerun.
    main()
