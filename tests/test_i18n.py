"""i18n guards — every catalog string is trilingual; dynamic translation is offline-safe."""

from __future__ import annotations

from project.i18n.translate import CATALOG, t, translate_dynamic

_LANGS = ("en", "si", "ta")


def test_catalog_complete_all_langs():
    missing = {
        key: [lang for lang in _LANGS if not entry.get(lang)]
        for key, entry in CATALOG.items()
        if not all(entry.get(lang) for lang in _LANGS)
    }
    assert not missing, f"CATALOG entries missing translations: {missing}"


def test_phase3_keys_present():
    # New strings added across Steps 5-6 must exist (catch a dropped key in review).
    for key in (
        "panel.booking.searching",
        "chat.voice_transcribing",
        "panel.rx.use_sample",
        "panel.rx.paste_btn",
        "panel.medicine.col_total",
    ):
        assert key in CATALOG, key


def test_translate_dynamic_offline_passthrough(no_api_key):
    assert translate_dynamic("Paracetamol 500mg", "si") == "Paracetamol 500mg"
    assert translate_dynamic("Paracetamol 500mg", "ta") == "Paracetamol 500mg"


def test_t_unknown_lang_falls_back_to_english():
    assert t("panel.booking.book", "xx") == t("panel.booking.book", "en")


def test_t_format_kwargs():
    out = t("panel.medicine.matched", "en", names="Paracetamol")
    assert "Paracetamol" in out
