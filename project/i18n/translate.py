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
    "sidebar.language_label":{"en": "Language", "si": "භාෂාව", "ta": "மொழி"},
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
    "sidebar.geo_unavail":  {"en": "(geolocation component unavailable — use manual entry below)",
                             "si": "(භූ-ස්ථානගත සංරචකය නොමැත — පහත අතින් ඇතුළත් කිරීම භාවිතා කරන්න)",
                             "ta": "(புவியிருப்பு கூறு கிடைக்கவில்லை — கீழே கைமுறை உள்ளீட்டைப் பயன்படுத்தவும்)"},
    "sidebar.geo_prompt":   {"en": "Click the 📍 button above, or enter coordinates manually:",
                             "si": "ඉහත 📍 බොත්තම ක්ලික් කරන්න, හෝ ඛණ්ඩාංක අතින් ඇතුළත් කරන්න:",
                             "ta": "மேலே உள்ள 📍 பொத்தானைக் கிளிக் செய்யவும், அல்லது ஆயங்களை கைமுறையாக உள்ளிடவும்:"},
    "sidebar.lat":          {"en": "Latitude", "si": "අක්ෂාංශය", "ta": "அட்சரேகை"},
    "sidebar.lng":          {"en": "Longitude", "si": "දේශාංශය", "ta": "தீர்க்கரேகை"},
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
    "chat.voice_failed":    {"en": "Could not transcribe — please try again or type.",
                             "si": "පිටපත් කළ නොහැකි විය — කරුණාකර නැවත උත්සාහ කරන්න හෝ type කරන්න.",
                             "ta": "எழுத்துப்படி மாற்ற முடியவில்லை — தயவுசெய்து மீண்டும் முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்."},
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
    "em.triggered_by":      {"en": "Triggered by", "si": "ක්‍රියාත්මක වූයේ", "ta": "தூண்டப்பட்டது"},
    "em.explain":           {"en": "If you confirm, MedBridge AI will show a tap-to-call link for Sri Lanka emergency services (**1990 Suwa Seriya**) and send a push notification to your saved family contact via ntfy.sh.",
                             "si": "ඔබ තහවුරු කළහොත්, MedBridge AI ශ්‍රී ලංකා හදිසි සේවා (**1990 සුව සැරිය**) සඳහා ඇමතුම් සබැඳියක් පෙන්වා, ntfy.sh හරහා ඔබේ පවුලේ සම්බන්ධතාවට push දැනුම්දීමක් යවයි.",
                             "ta": "நீங்கள் உறுதிப்படுத்தினால், MedBridge AI இலங்கை அவசர சேவைகளுக்கான (**1990 சுவசெரிய**) அழைப்பு இணைப்பைக் காட்டி, ntfy.sh வழியாக உங்கள் குடும்ப தொடர்பாளருக்கு push அறிவிப்பு அனுப்பும்."},
    "em.push_failed":       {"en": "Family push notification could not be sent (logged regardless). Please call 1990.",
                             "si": "පවුල් push දැනුම්දීම යැවිය නොහැකි විය (කෙසේ වෙතත් සටහන් කරන ලදී). කරුණාකර 1990 අමතන්න.",
                             "ta": "குடும்ப push அறிவிப்பை அனுப்ப முடியவில்லை (இருப்பினும் பதிவு செய்யப்பட்டது). தயவுசெய்து 1990 ஐ அழைக்கவும்."},
    "em.dismiss_continue":  {"en": "Dismiss and continue chatting",
                             "si": "ඉවත් කර කතාබහ දිගටම කරගෙන යන්න",
                             "ta": "அகற்றிவிட்டு அரட்டையைத் தொடரவும்"},
    # ---- panels (booking/medicine/report) ----
    "panel.booking.title":  {"en": "Booking suggestions",
                             "si": "වේලාව වෙන් කිරීමේ යෝජනා",
                             "ta": "முன்பதிவு பரிந்துரைகள்"},
    "panel.booking.book":   {"en": "Book", "si": "වෙන් කරන්න", "ta": "பதிவு செய்"},
    "panel.booking.fee":    {"en": "Fee", "si": "ගාස්තුව", "ta": "கட்டணம்"},
    "panel.booking.no_alts":{"en": "No available alternatives in the next week. Try another doctor or specialty.",
                             "si": "ඉදිරි සතිය තුළ විකල්ප කිසිවක් නොමැත. වෙනත් වෛද්‍යවරයෙකු හෝ විශේෂඥතාවක් උත්සාහ කරන්න.",
                             "ta": "அடுத்த வாரத்தில் மாற்று நேரங்கள் இல்லை. வேறு மருத்துவர் அல்லது சிறப்புத்துறையை முயற்சிக்கவும்."},
    "panel.booking.dismiss":{"en": "Dismiss", "si": "ඉවත් කරන්න", "ta": "அகற்று"},
    "panel.booking.dismiss_all":{"en": "Dismiss booking suggestions",
                             "si": "වෙන්කිරීමේ යෝජනා ඉවත් කරන්න",
                             "ta": "முன்பதிவு பரிந்துரைகளை அகற்று"},
    "panel.booking.slot_taken":{"en": "That slot was just taken — please pick another.",
                             "si": "එම වේලාව දැන් ගෙන ඇත — කරුණාකර වෙනත් එකක් තෝරන්න.",
                             "ta": "அந்த நேரம் இப்போது எடுக்கப்பட்டது — தயவுசெய்து வேறொன்றைத் தேர்ந்தெடுக்கவும்."},
    "panel.booking.booked": {"en": "Booked with {doctor} on {date} at {time}. Push notification sent.",
                             "si": "{doctor} සමඟ {date} දින {time} ට වෙන් කරන ලදී. Push දැනුම්දීම යවන ලදී.",
                             "ta": "{doctor} உடன் {date} அன்று {time} மணிக்கு பதிவு செய்யப்பட்டது. Push அறிவிப்பு அனுப்பப்பட்டது."},
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
    "panel.report.caption": {"en": "Three independent specialists (cardiology, internal medicine, radiology) each read the SAME report without seeing each other's output. A moderator then surfaces points of agreement and disagreement. Reports are text-only in this build.",
                             "si": "ස්වාධීන විශේෂඥයන් තිදෙනෙක් (හෘද රෝග, අභ්‍යන්තර වෛද්‍ය, විකිරණවේද) එකම වාර්තාව එකිනෙකාගේ ප්‍රතිදානය නොබලා කියවයි. පසුව මැදිහත්කරුවෙක් එකඟතා සහ එකඟ නොවීම් ඉදිරිපත් කරයි. මෙම නිර්මාණයේ වාර්තා පෙළ පමණි.",
                             "ta": "மூன்று சுயாதீன நிபுணர்கள் (இதயவியல், உள் மருத்துவம், கதிரியக்கவியல்) ஒருவரின் வெளியீட்டை மற்றவர் பார்க்காமல் அதே அறிக்கையைப் படிக்கிறார்கள். பின்னர் ஒரு மதிப்பீட்டாளர் உடன்பாடு மற்றும் கருத்து வேறுபாடுகளை வெளிப்படுத்துகிறார். இந்த பதிப்பில் அறிக்கைகள் உரை மட்டுமே."},
    "panel.report.none":    {"en": "— none —", "si": "— කිසිවක් නැත —", "ta": "— எதுவுமில்லை —"},
    "panel.report.pick_sample":{"en": "Pick a sample report (or use upload / paste below)",
                             "si": "නියැදි වාර්තාවක් තෝරන්න (හෝ පහත උඩුගත / අලවන්න භාවිතා කරන්න)",
                             "ta": "மாதிரி அறிக்கையைத் தேர்ந்தெடுக்கவும் (அல்லது கீழே பதிவேற்று / ஒட்டு)"},
    "panel.report.upload":  {"en": "Or upload a .txt report",
                             "si": "හෝ .txt වාර්තාවක් උඩුගත කරන්න",
                             "ta": "அல்லது .txt அறிக்கையைப் பதிவேற்றவும்"},
    "panel.report.paste":   {"en": "Or paste report text directly",
                             "si": "හෝ වාර්තා පෙළ කෙලින්ම අලවන්න",
                             "ta": "அல்லது அறிக்கை உரையை நேரடியாக ஒட்டவும்"},
    "panel.report.paste_ph":{"en": "Paste the full report text here…",
                             "si": "සම්පූර්ණ වාර්තා පෙළ මෙහි අලවන්න…",
                             "ta": "முழு அறிக்கை உரையையும் இங்கே ஒட்டவும்…"},
    "panel.report.need_input":{"en": "Provide a report via sample, upload, or paste.",
                             "si": "නියැදිය, උඩුගත කිරීම හෝ අලවීම හරහා වාර්තාවක් සපයන්න.",
                             "ta": "மாதிரி, பதிவேற்றம் அல்லது ஒட்டுதல் மூலம் அறிக்கையை வழங்கவும்."},
    "panel.report.spin_specialists":{"en": "Three specialists reviewing independently…",
                             "si": "විශේෂඥයන් තිදෙනෙක් ස්වාධීනව සමාලෝචනය කරමින්…",
                             "ta": "மூன்று நிபுணர்கள் சுயாதீனமாக மதிப்பாய்வு செய்கின்றனர்…"},
    "panel.report.spin_moderator":{"en": "Moderator synthesising…",
                             "si": "මැදිහත්කරු සංශ්ලේෂණය කරමින්…",
                             "ta": "மதிப்பீட்டாளர் தொகுக்கிறார்…"},
    "panel.report.opinions_header":{"en": "Specialist opinions — report #{id}",
                             "si": "විශේෂඥ අදහස් — වාර්තාව #{id}",
                             "ta": "நிபுணர் கருத்துகள் — அறிக்கை #{id}"},
    "panel.report.lbl_cardiology":{"en": "🫀 Cardiology", "si": "🫀 හෘද රෝග", "ta": "🫀 இதயவியல்"},
    "panel.report.lbl_internal":{"en": "🩺 Internal medicine", "si": "🩺 අභ්‍යන්තර වෛද්‍ය", "ta": "🩺 உள் மருத்துவம்"},
    "panel.report.lbl_radiology":{"en": "🖼️ Radiology", "si": "🖼️ විකිරණවේදය", "ta": "🖼️ கதிரியக்கவியல்"},
    "panel.report.confidence":{"en": "Confidence", "si": "විශ්වාසය", "ta": "நம்பிக்கை"},
    "panel.report.flags":   {"en": "Flags", "si": "ධජ", "ta": "கொடிகள்"},
    "panel.report.consensus_header":{"en": "Moderator consensus",
                             "si": "මැදිහත්කරුගේ එකඟතාව",
                             "ta": "மதிப்பீட்டாளர் ஒருமித்த கருத்து"},
    "panel.report.summary": {"en": "Summary.", "si": "සාරාංශය.", "ta": "சுருக்கம்."},
    "panel.report.agreement":{"en": "Points of agreement",
                             "si": "එකඟ වන කරුණු",
                             "ta": "உடன்பாட்டுப் புள்ளிகள்"},
    "panel.report.disagreement":{"en": "Points of disagreement",
                             "si": "එකඟ නොවන කරුණු",
                             "ta": "கருத்து வேறுபாட்டுப் புள்ளிகள்"},
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
