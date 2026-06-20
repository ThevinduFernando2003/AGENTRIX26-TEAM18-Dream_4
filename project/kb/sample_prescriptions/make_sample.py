"""Regenerate the demo prescription image + its plain-text transcription.

This sample is SYNTHETIC seed data — not a real prescription. The drug names are
chosen from project/kb/seed_medicines.json so the downstream pharmacy comparison
returns results. Dosage lines are the doctor's *instruction* (free text); the app
always shows the catalog's reference_dosage_text verbatim, never these.

Run from the repo root:  python project/kb/sample_prescriptions/make_sample.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_HERE = Path(__file__).resolve().parent

# The transcription the app should end up with (also used to pre-fill the confirm
# gate offline, when Gemini Vision is unavailable and OCR returns "").
TRANSCRIPTION = """City Clinic — Dr. A. Perera
Patient: Nimal Perera

Rx:
Paracetamol 500mg — 1 tablet three times daily
Amoxicillin 500mg — 1 capsule twice daily for 5 days
Cetirizine 10mg — 1 tablet at night"""

# Lines as drawn on the image (with a clear DEMO marker so it can't be mistaken
# for a real prescription).
_IMAGE_LINES = [
    "City Clinic  —  Dr. A. Perera",
    "(SEED / DEMO — not a real prescription)",
    "",
    "Patient: Nimal Perera",
    "",
    "Rx:",
    "   Paracetamol 500mg  —  1 tablet three times daily",
    "   Amoxicillin 500mg  —  1 capsule twice daily for 5 days",
    "   Cetirizine 10mg    —  1 tablet at night",
    "",
    "Signature: A. Perera",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ("arial.ttf", "DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def main() -> None:
    _HERE.mkdir(parents=True, exist_ok=True)
    (_HERE / "sample_rx_en.txt").write_text(TRANSCRIPTION + "\n", encoding="utf-8")

    width, top, line_h = 760, 28, 40
    height = top * 2 + line_h * len(_IMAGE_LINES)
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([6, 6, width - 7, height - 7], outline="#334155", width=2)
    title_font, body_font = _font(26), _font(22)
    for i, line in enumerate(_IMAGE_LINES):
        d.text((28, top + i * line_h), line, fill="black", font=title_font if i == 0 else body_font)
    img.save(_HERE / "sample_rx_en.png")
    print(f"Wrote {_HERE / 'sample_rx_en.png'} and sample_rx_en.txt")


if __name__ == "__main__":
    main()
