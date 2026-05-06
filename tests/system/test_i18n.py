"""Tests fuer ccc.system.i18n — 4 Cases (3 Standard + 1 Fallback-Coverage)."""

from __future__ import annotations

from ccc.system.i18n import t


# Case 1: DE-Lookup
def test_t_returns_de_string():
    assert t("back", "DE") == "Zurück"
    assert t("apply", "DE") == "Anwenden"


# Case 2: EN-Lookup
def test_t_returns_en_string():
    assert t("back", "EN") == "Back"
    assert t("apply", "EN") == "Apply"


# Case 3: Missing key -> marker (kein KeyError-Crash)
def test_t_missing_key_returns_marker():
    assert t("nonexistent_key") == "<missing:nonexistent_key>"
    assert t("nonexistent_key", "EN") == "<missing:nonexistent_key>"


# Case 4: Unknown lang fallback to DE (Senior-Schaerfung Coverage-Symmetrie)
def test_t_unknown_lang_falls_back_to_de():
    assert t("back", "XX") == "Zurück"  # XX nicht in STRINGS -> DE-Fallback
    assert t("apply", "FR") == "Anwenden"  # FR auch nicht
