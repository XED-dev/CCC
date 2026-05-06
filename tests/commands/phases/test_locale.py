"""Tests fuer ccc.commands.phases.locale — 4 Cases."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ccc.commands.phases.locale import apply_locales, apply_timezone


# Case 1: apply_timezone Happy-Path mit Optional-Args
@patch("ccc.commands.phases.locale.subprocess.run")
def test_apply_timezone_happy_path(mock_run, tmp_path):
    zoneinfo_dir = tmp_path / "zoneinfo"
    zoneinfo_dir.mkdir()
    (zoneinfo_dir / "UTC").touch()
    timezone_file = tmp_path / "timezone"

    apply_timezone(
        "UTC",
        zoneinfo_dir=zoneinfo_dir,
        timezone_file=timezone_file,
    )

    assert timezone_file.read_text() == "UTC\n"
    # 2 subprocess-Aufrufe: ln -sfn + dpkg-reconfigure
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].args[0][:2] == ["ln", "-sfn"]
    assert mock_run.call_args_list[1].args[0][0] == "dpkg-reconfigure"


# Case 2: apply_timezone unbekannte TZ -> RuntimeError
@patch("ccc.commands.phases.locale.subprocess.run")
def test_apply_timezone_unknown_tz_raises(mock_run, tmp_path):
    zoneinfo_dir = tmp_path / "zoneinfo"
    zoneinfo_dir.mkdir()
    # NICHT UTC erzeugen -> apply_timezone soll RuntimeError werfen

    with pytest.raises(RuntimeError, match="Unbekannte Zeitzone"):
        apply_timezone("Mars/Olympus", zoneinfo_dir=zoneinfo_dir)
    assert mock_run.call_count == 0


# Case 3: apply_locales — enable + disable + append (drei Cases im Diff)
@patch("ccc.commands.phases.locale.subprocess.run")
def test_apply_locales_enable_disable_append(mock_run, tmp_path):
    locale_gen = tmp_path / "locale.gen"
    # ACTIVE: en_US (soll deaktiviert werden, weil nicht in target_locales)
    # DISABLED: de_DE (soll aktiviert werden = uncomment)
    # ABSENT: fr_FR (soll angehängt werden)
    locale_gen.write_text(
        "en_US.UTF-8 UTF-8\n"
        "# de_DE.UTF-8 UTF-8\n"
    )
    target_locales = ["de_DE.UTF-8", "fr_FR.UTF-8"]
    apply_locales(
        target_locales, "de_DE.UTF-8",
        locale_gen=locale_gen,
        menu_list=("en_US.UTF-8", "de_DE.UTF-8", "fr_FR.UTF-8"),
    )
    content = locale_gen.read_text()
    # uncommented (de_DE wurde von '# de_DE...' auf 'de_DE...' transformiert)
    assert "\nde_DE.UTF-8 UTF-8" in content or content.startswith("de_DE.UTF-8 UTF-8")
    assert "# de_DE.UTF-8" not in content
    # disabled (en_US bekam '# ' prefix)
    assert "# en_US.UTF-8 UTF-8" in content
    # appended
    assert "fr_FR.UTF-8 UTF-8" in content
    # 2 subprocess-Aufrufe: locale-gen + update-locale
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].args[0][0] == "locale-gen"
    assert mock_run.call_args_list[1].args[0][0] == "update-locale"


# Case 4: apply_locales — alles bereits korrekt -> Datei unverändert,
# locale-gen + update-locale laufen trotzdem (Default-Locale immer setzen)
@patch("ccc.commands.phases.locale.subprocess.run")
def test_apply_locales_no_changes(mock_run, tmp_path):
    locale_gen = tmp_path / "locale.gen"
    locale_gen.write_text("de_AT.UTF-8 UTF-8\n")
    initial_content = locale_gen.read_text()
    apply_locales(
        ["de_AT.UTF-8"], "de_AT.UTF-8",
        locale_gen=locale_gen,
        menu_list=("de_AT.UTF-8",),
    )
    assert locale_gen.read_text() == initial_content  # unverändert
    # locale-gen + update-locale trotzdem aufgerufen (Default-Locale setzen)
    assert mock_run.call_count == 2
