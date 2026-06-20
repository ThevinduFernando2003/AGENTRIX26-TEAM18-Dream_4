"""i18n: static catalog of UI strings + dynamic LLM translation.

- `t(key, lang)` returns a translated UI label from the static
  CATALOG. Unknown keys/langs fall back to English.
- `translate_dynamic(text, lang)` runs Gemini for free-form agent
  replies. Cached per process so the same reply isn't re-translated
  on every Streamlit rerun.

Disclaimer translations are pre-baked (not LLM-translated) so the
wording is reviewable and never drifts.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Literal

logger = logging.getLogger("medbridge.i18n")

LANG = Literal["en", "si", "ta"]
LANG_NAMES = {"en": "English", "si": "Sinhala", "ta": "Tamil"}


CATALOG: dict[str, dict[str, str]] = {
    # ---- auth ----
    "auth.title":           {"en": "MedBridge AI",
                             "si": "මෙඩ්බ්‍රිජ් AI",
                             "ta": "மெட்பிரிட்ஜ் AI"},
    "auth.tagline":         {"en": "Multi-agent healthcare navigator — demo build (Team Dream_4)",
                             "si": "බහු-නියෝජිත සෞඛ්‍ය මාර්ගෝපදේශක — demo build (Team Dream_4)",
                             "ta": "பல-முகவர் சுகாதார வழிகாட்டி — demo build (Team Dream_4)"},
    "auth.tab.login":       {"en": "Log in", "si": "පුරන්න", "ta": "உள்நுழை"},
    "auth.tab.signup":      {"en": "Sign up", "si": "ලියාපදිංචි වන්න", "ta": "பதிவு செய்"},
    "auth.username":        {"en": "Username", "si": "පරිශීලක නාමය", "ta": "பயனர்பெயர்"},
    "auth.password":        {"en": "Password", "si": "මුරපදය", "ta": "கடவுச்சொல்"},
    "auth.fullname":        {"en": "Full name", "si": "සම්පූර්ණ නම", "ta": "முழுப்பெயர்"},
    "auth.age":             {"en": "Age", "si": "වයස", "ta": "வயது"},
    "auth.gender":          {"en": "Gender", "si": "ස්ත්‍රී/පුරුෂ භාවය", "ta": "பாலினம்"},
    "auth.pref_lang":       {"en": "Preferred language", "si": "කැමති භාෂාව", "ta": "விருப்ப மொழி"},
    "auth.family_name":     {"en": "Family contact name (for emergency push)",
                             "si": "පවුලේ සම්බන්ධතා නම (හදිසි දැනුම්දීම සඳහා)",
                             "ta": "குடும்ப தொடர்பு பெயர் (அவசர அறிவிப்புக்கு)"},
    "auth.family_phone":    {"en": "Family contact phone",
                             "si": "පවුලේ සම්බන්ධතා දුරකථන",
                             "ta": "குடும்ப தொடர்பு தொலைபேசி"},
    "auth.login_btn":       {"en": "Log in", "si": "පුරන්න", "ta": "உள்நுழை"},
    "auth.signup_btn":      {"en": "Create account", "si": "ගිණුම සාදන්න", "ta": "கணக்கை உருவாக்கு"},
    "auth.invalid":         {"en": "Invalid username or password.",
                             "si": "පරිශීලක නාමය හෝ මුරපදය වැරදිය.",
                             "ta": "தவறான பயனர்பெயர் அல்லது கடவுச்சொல்."},
    # ---- sidebar ----
    "sidebar.mock_banner":  {"en": "Demo build — all facility, doctor, slot, pharmacy and price data is SEED / MOCK data.",
                             "si": "Demo build — සියලුම පහසුකම්, වෛද්‍ය, වේලාව, ෆාමසි සහ මිල දත්ත SEED / MOCK දත්ත වේ.",
                             "ta": "Demo build — அனைத்து வசதி, மருத்துவர், நேரம், மருந்தகம் மற்றும் விலை தரவும் SEED / MOCK தரவு ஆகும்."},
    "sidebar.topic_label":  {"en": "Family-alert push topic",
                             "si": "පවුල් අනතුරු ඇඟවීමේ Push මාතෘකාව",
                             "ta": "குடும்ப எச்சரிக்கை Push தலைப்பு"},
    "sidebar.topic_caption":{"en": "Family subscribes at https://ntfy.sh/{topic} (free, no signup) to get emergency notifications.",
                             "si": "පවුලේ අය හදිසි දැනුම්දීම් ලබා ගැනීමට https://ntfy.sh/{topic} හි (නොමිලේ, ලියාපදිංචියකින් තොරව) දායක වෙති.",
                             "ta": "அவசர அறிவிப்புகளைப் பெற குடும்பத்தினர் https://ntfy.sh/{topic} இல் (இலவசம், பதிவு தேவையில்லை) குழுசேருகிறார்கள்."},
    "sidebar.location":     {"en": "Your location (for pharmacy distance)",
                             "si": "ඔබේ ස්ථානය (ෆාමසි දුර සඳහා)",
                             "ta": "உங்கள் இருப்பிடம் (மருந்தக தூரத்திற்கு)"},
    "sidebar.location_manual":{"en": "Enter coordinates manually",
                               "si": "ඛණ්ඩාංක අතින් ඇතුළත් කරන්න",
                               "ta": "ஆயங்களை கைமுறையாக உள்ளிடவும்"},
    "sidebar.use_coords":   {"en": "Use these coordinates",
                             "si": "මෙම ඛණ්ඩාංක භාවිතා කරන්න",
                             "ta": "இந்த ஆயங்களைப் பயன்படுத்துக"},
    "sidebar.logout":       {"en": "Log out", "si": "ඉවත් වන්න", "ta": "வெளியேறு"},
    "sidebar.tts_toggle":   {"en": "🔊 Speak assistant replies",
                             "si": "🔊 සහායකගේ පිළිතුරු කථනය කරන්න",
                             "ta": "🔊 உதவியாளரின் பதில்களை பேசவும்"},
    "sidebar.reminders_btn":{"en": "🔔 Check my reminders",
                             "si": "🔔 මගේ මතක්කිරීම් පරීක්ෂා කරන්න",
                             "ta": "🔔 எனது நினைவூட்டல்களை சரிபார்"},
    "sidebar.reminders_none":{"en": "No reminders due in the next 7 days.",
                              "si": "ඉදිරි දින 7 තුළ මතක් කිරීම් කිසිවක් නොමැත.",
                              "ta": "அடுத்த 7 நாட்களில் எந்த நினைவூட்டலும் இல்லை."},
    "sidebar.reminders_send":{"en": "Send push for {n} reminder(s) now",
                              "si": "දැන් මතක් කිරීම් {n} සඳහා push යවන්න",
                              "ta": "இப்போது {n} நினைவூட்டல்(களுக்கு) push அனுப்பு"},
    "sidebar.reminders_sent":{"en": "Sent {n} push notification(s).",
                              "si": "Push දැනුම්දීම් {n} ක් යවන ලදී.",
                              "ta": "{n} Push அறிவிப்புகள் அனுப்பப்பட்டன."},
    # ---- chat ----
    "app.title":            {"en": "🩺 MedBridge AI",
                             "si": "🩺 මෙඩ්බ්‍රිජ් AI",
                             "ta": "🩺 மெட்பிரிட்ஜ் AI"},
    "app.caption":          {"en": "Multi-agent healthcare navigator — Team Dream_4 · AgenTrix 2026",
                             "si": "බහු-නියෝජිත සෞඛ්‍ය මාර්ගෝපදේශක — Team Dream_4 · AgenTrix 2026",
                             "ta": "பல-முகவர் சுகாதார வழிகாட்டி — Team Dream_4 · AgenTrix 2026"},
    "chat.placeholder":     {"en": "Describe your symptoms, or ask to book an appointment or check medicine prices…",
                             "si": "ඔබේ රෝග ලක්ෂණ විස්තර කරන්න, හෝ වෙලාවක් වෙන්කිරීමට හෝ ඖෂධ මිල පරීක්ෂා කිරීමට කියන්න…",
                             "ta": "உங்கள் அறிகுறிகளை விவரிக்கவும், அல்லது சந்திப்பு பதிவு செய்ய அல்லது மருந்து விலையை சரிபார்க்க கேட்கவும்…"},
    "chat.voice_expander":  {"en": "🎙️ Voice input (Sinhala / Tamil / English)",
                             "si": "🎙️ හඬ ආදානය (සිංහල / දෙමළ / ඉංග්‍රීසි)",
                             "ta": "🎙️ குரல் உள்ளீடு (சிங்களம் / தமிழ் / ஆங்கிலம்)"},
    "chat.voice_transcribe":{"en": "Transcribe & send",
                             "si": "පිටපත් කර යවන්න",
                             "ta": "எழுதி அனுப்பு"},
    "chat.voice_unavail":   {"en": "Voice input needs GEMINI_API_KEY. Type instead, or set the key.",
                             "si": "හඬ ආදානයට GEMINI_API_KEY අවශ්‍යයි. ඒ වෙනුවට type කරන්න, හෝ යතුර සකසන්න.",
                             "ta": "குரல் உள்ளீட்டுக்கு GEMINI_API_KEY தேவை. அதற்கு பதிலாக தட்டச்சு செய்யவும், அல்லது விசையை அமைக்கவும்."},
    # ---- emergency ----
    "em.title":             {"en": "🚨 Possible medical emergency detected",
                             "si": "🚨 හදිසි වෛද්‍ය තත්ත්වයක් අනාවරණය විය හැක",
                             "ta": "🚨 சாத்தியமான மருத்துவ அவசரநிலை கண்டறியப்பட்டது"},
    "em.confirm":           {"en": "✅ Yes, this is an emergency",
                             "si": "✅ ඔව්, මෙය හදිසි අවස්ථාවකි",
                             "ta": "✅ ஆம், இது அவசரநிலை"},
    "em.dismiss":           {"en": "❌ No, false alarm",
                             "si": "❌ නැත, වැරදි අනතුරු ඇඟවීමයි",
                             "ta": "❌ இல்லை, தவறான எச்சரிக்கை"},
    "em.call_btn":          {"en": "📞  Call 1990 now (Suwa Seriya Ambulance)",
                             "si": "📞  දැන් 1990 අමතන්න (සුව සැරිය ගිලන් රථය)",
                             "ta": "📞  இப்போது 1990 அழைக்கவும் (சுவசெரிய ஆம்புலன்ஸ்)"},
    "em.family_notified":   {"en": "Family contact notified via ntfy.sh.",
                             "si": "පවුලේ සම්බන්ධතාව ntfy.sh හරහා දැනුවත් කරන ලදී.",
                             "ta": "குடும்ப தொடர்பாளர் ntfy.sh வழியாக அறிவிக்கப்பட்டார்."},
    # ---- panels (booking/medicine/report) ----
    "panel.booking.title":  {"en": "Booking suggestions",
                             "si": "වේලාව වෙන් කිරීමේ යෝජනා",
                             "ta": "முன்பதிவு பரிந்துரைகள்"},
    "panel.booking.book":   {"en": "Book", "si": "වෙන් කරන්න", "ta": "பதிவு செய்"},
    "panel.medicine.title": {"en": "Pharmacy comparison",
                             "si": "ෆාමසි සංසන්දනය",
                             "ta": "மருந்தக ஒப்பீடு"},
    "panel.medicine.matched":{"en": "Matched: {names}",
                             "si": "ගැළපුණු: {names}",
                             "ta": "பொருந்தியவை: {names}"},
    "panel.medicine.unmatched":{"en": "Not in (demo) catalog: {names}",
                             "si": "(demo) නාමාවලියේ නැත: {names}",
                             "ta": "(demo) பட்டியலில் இல்லை: {names}"},
    "panel.medicine.col_pharmacy":{"en": "Pharmacy", "si": "ෆාමසිය", "ta": "மருந்தகம்"},
    "panel.medicine.col_address":{"en": "Address", "si": "ලිපිනය", "ta": "முகவரி"},
    "panel.medicine.col_items":{"en": "Items", "si": "අයිතම", "ta": "பொருட்கள்"},
    "panel.medicine.col_total":{"en": "Total (LKR)", "si": "එකතුව (LKR)", "ta": "மொத்தம் (LKR)"},
    "panel.medicine.col_distance":{"en": "Distance (km)", "si": "දුර (km)", "ta": "தூரம் (km)"},
    "panel.medicine.col_missing":{"en": "Out of stock", "si": "තොගයේ නැත", "ta": "கையிருப்பில் இல்லை"},
    "panel.medicine.dismiss":{"en": "Dismiss medicine results",
                             "si": "ඖෂධ ප්‍රතිඵල ඉවත් කරන්න",
                             "ta": "மருந்து முடிவுகளை அகற்று"},
    # ---- prescription (OCR + confirm gate) ----
    "panel.rx.expander":    {"en": "💊 Prescription photo (OCR + confirm gate)",
                             "si": "💊 බෙහෙත් වට්ටෝරු ඡායාරූපය (OCR + තහවුරු කිරීමේ දොරටුව)",
                             "ta": "💊 மருந்துச்சீட்டு புகைப்படம் (OCR + உறுதிப்படுத்தல் வாயில்)"},
    "panel.rx.caption":     {"en": "Upload a prescription photo. Gemini Vision will transcribe it. You MUST confirm the transcription is exactly what your prescription says before we search any pharmacy. We never invent or modify dosage text.",
                             "si": "බෙහෙත් වට්ටෝරුවක ඡායාරූපයක් උඩුගත කරන්න. Gemini Vision එය පිටපත් කරයි. ඕනෑම ෆාමසියක් සෙවීමට පෙර, පිටපත ඔබේ වට්ටෝරුවේ ඇති දේ හරියටම බව ඔබ තහවුරු කළ යුතුය. අපි කිසි විටෙක මාත්‍රා පෙළ නිර්මාණය හෝ වෙනස් නොකරමු.",
                             "ta": "மருந்துச்சீட்டு புகைப்படத்தைப் பதிவேற்றவும். Gemini Vision அதை எழுத்துப்படி மாற்றும். எந்த மருந்தகத்தையும் தேடுவதற்கு முன், எழுத்துப்படி மாற்றியது உங்கள் மருந்துச்சீட்டில் உள்ளதைப் போலவே உள்ளது என்பதை நீங்கள் உறுதிப்படுத்த வேண்டும். மருந்தளவு உரையை நாங்கள் ஒருபோதும் உருவாக்கவோ மாற்றவோ மாட்டோம்."},
    "panel.rx.unavailable": {"en": "Gemini Vision is unavailable (no GEMINI_API_KEY). You can still paste your prescription text below.",
                             "si": "Gemini Vision ලද නොහැක (GEMINI_API_KEY නැත). ඔබට තවමත් පහත ඔබේ වට්ටෝරු පෙළ අලවන්න පුළුවන.",
                             "ta": "Gemini Vision கிடைக்கவில்லை (GEMINI_API_KEY இல்லை). கீழே உங்கள் மருந்துச்சீட்டு உரையை இன்னும் ஒட்டலாம்."},
    "panel.rx.upload":      {"en": "Upload prescription photo (PNG/JPG)",
                             "si": "බෙහෙත් වට්ටෝරු ඡායාරූපය උඩුගත කරන්න (PNG/JPG)",
                             "ta": "மருந்துச்சீட்டு புகைப்படத்தைப் பதிவேற்று (PNG/JPG)"},
    "panel.rx.transcribe":  {"en": "Transcribe with Gemini Vision",
                             "si": "Gemini Vision සමඟ පිටපත් කරන්න",
                             "ta": "Gemini Vision மூலம் எழுத்துப்படி மாற்று"},
    "panel.rx.spinner":     {"en": "Running OCR…",
                             "si": "OCR ක්‍රියාත්මක වෙමින්…",
                             "ta": "OCR இயங்குகிறது…"},
    "panel.rx.confirm_prompt":{"en": "**Is this exactly what's written on your prescription?** Edit the text below if anything is wrong, then confirm.",
                             "si": "**මෙය ඔබේ වට්ටෝරුවේ ලියා ඇති දේ හරියටම ද?** යමක් වැරදි නම් පහත පෙළ සංස්කරණය කර, ඉන්පසු තහවුරු කරන්න.",
                             "ta": "**இது உங்கள் மருந்துச்சீட்டில் எழுதப்பட்டுள்ளதைப் போலவே உள்ளதா?** ஏதேனும் தவறாக இருந்தால் கீழே உள்ள உரையைத் திருத்தி, பின்னர் உறுதிப்படுத்தவும்."},
    "panel.rx.edit_label":  {"en": "Transcribed prescription (editable)",
                             "si": "පිටපත් කළ වට්ටෝරුව (සංස්කරණය කළ හැක)",
                             "ta": "எழுத்துப்படி மாற்றப்பட்ட மருந்துச்சீட்டு (திருத்தக்கூடியது)"},
    "panel.rx.confirm_btn": {"en": "✅ Yes — search pharmacies",
                             "si": "✅ ඔව් — ෆාමසි සොයන්න",
                             "ta": "✅ ஆம் — மருந்தகங்களைத் தேடு"},
    "panel.rx.discard_btn": {"en": "❌ Discard and start over",
                             "si": "❌ ඉවත් කර නැවත අරඹන්න",
                             "ta": "❌ நிராகரித்து மீண்டும் தொடங்கு"},
    "panel.report.title":   {"en": "📄 Specialist Panel report review",
                             "si": "📄 විශේෂඥ මණ්ඩලයේ වාර්තා සමාලෝචනය",
                             "ta": "📄 நிபுணர் குழுவின் அறிக்கை மதிப்பாய்வு"},
    "panel.report.run":     {"en": "Run Specialist Panel",
                             "si": "විශේෂඥ මණ්ඩලය ක්‍රියාත්මක කරන්න",
                             "ta": "நிபுணர் குழுவை இயக்கவும்"},
    # ---- disclaimer ----
    "disclaimer.footer":    {"en": "_This is an AI-generated observation, not a medical diagnosis. Please consult a licensed physician or pharmacist._",
                             "si": "_මෙය AI විසින් උපදවන ලද නිරීක්ෂණයකි, වෛද්‍ය රෝග විනිශ්චයක් නොවේ. කරුණාකර බලපත්‍රලාභී වෛද්‍යවරයෙකු හෝ ඖෂධවේදියෙකු හමුවන්න._",
                             "ta": "_இது AI-ஆல் உருவாக்கப்பட்ட கருத்து, மருத்துவ நோய் கண்டறிதல் அல்ல. தயவுசெய்து உரிமம் பெற்ற மருத்துவர் அல்லது மருந்தாளரை அணுகவும்._"},
}


def t(key: str, lang: str = "en", **fmt: str) -> str:
    """Look up a localised string. Falls back to English if missing."""
    entry = CATALOG.get(key)
    if entry is None:
        return key  # surface the missing key in dev rather than crashing
    val = entry.get(lang) or entry.get("en") or key
    if fmt:
        try:
            return val.format(**fmt)
        except (KeyError, IndexError):
            return val
    return val


@lru_cache(maxsize=512)
def _translate_cached(text: str, lang: str, model_id: str) -> str:
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel(model_id)
        prompt = (
            f"Translate the following text to {LANG_NAMES.get(lang, lang)}. "
            "Preserve all numbers, drug names, doctor names, and dosages exactly. "
            "Return ONLY the translation, no commentary, no quotes.\n\n"
            f"--- Text ---\n{text}\n--- End ---"
        )
        resp = model.generate_content(prompt)
        out = (getattr(resp, "text", "") or "").strip()
        return out or text
    except Exception as exc:
        logger.warning("translate_dynamic failed (%s): %s", lang, exc)
        return text


def translate_dynamic(text: str, lang: str) -> str:
    if not text or lang == "en":
        return text
    if not os.environ.get("GEMINI_API_KEY"):
        return text
    model_id = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    return _translate_cached(text, lang, model_id)
