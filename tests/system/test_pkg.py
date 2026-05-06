"""Tests fuer ccc.system.pkg — 5 Cases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ccc.system.pkg import (
    current_default_locale,
    is_installed,
    locale_state,
    locale_status,
    locale_status_in_content,
    pkg_state,
)


# Case 1: is_installed beide Status-Werte (kombiniert)
@patch("ccc.system.pkg.subprocess.run")
def test_is_installed_states(mock_run):
    # True-Pfad
    mock_run.return_value = MagicMock(returncode=0, stdout="install ok installed")
    assert is_installed("htop") is True
    # False-Pfad: Paket entfernt aber config-files da
    mock_run.return_value = MagicMock(returncode=0, stdout="deinstall ok config-files")
    assert is_installed("htop") is False
    # False-Pfad: dpkg-query gibt non-zero zurueck (Paket gar nicht bekannt)
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    assert is_installed("nonexistent") is False


# Case 2: locale_status drei-wertige Erkennung
def test_locale_status_three_states(tmp_path):
    locale_gen = tmp_path / "locale.gen"
    locale_gen.write_text(
        "de_AT.UTF-8 UTF-8\n"
        "# de_DE.UTF-8 UTF-8\n"
        "# en_US.UTF-8 UTF-8\n"
    )
    assert locale_status("de_AT.UTF-8", locale_gen=locale_gen) == "ACTIVE"
    assert locale_status("de_DE.UTF-8", locale_gen=locale_gen) == "DISABLED"
    assert locale_status("fr_FR.UTF-8", locale_gen=locale_gen) == "ABSENT"


# Case 3: pkg_state drei Pfade
@patch("ccc.system.pkg.is_first_run")
@patch("ccc.system.pkg.is_installed")
def test_pkg_state_logic(mock_installed, mock_first_run):
    # Installed -> ON
    mock_installed.return_value = True
    mock_first_run.return_value = False
    assert pkg_state("htop", default="ON") == "ON"
    # Nicht installed + first_run -> default
    mock_installed.return_value = False
    mock_first_run.return_value = True
    assert pkg_state("pwgen", default="ON") == "ON"
    assert pkg_state("pwgen", default="OFF") == "OFF"
    # Nicht installed + re_run -> OFF
    mock_installed.return_value = False
    mock_first_run.return_value = False
    assert pkg_state("pwgen", default="ON") == "OFF"


# Case 4: locale_state vier Pfade (analog pkg_state, aber drei-wertig via locale_status)
@patch("ccc.system.pkg.is_first_run")
@patch("ccc.system.pkg.locale_status")
def test_locale_state_logic(mock_status, mock_first_run):
    mock_status.return_value = "ACTIVE"
    assert locale_state("de_AT.UTF-8") == "ON"
    mock_status.return_value = "DISABLED"
    assert locale_state("de_AT.UTF-8") == "OFF"
    mock_status.return_value = "ABSENT"
    mock_first_run.return_value = True
    assert locale_state("de_AT.UTF-8", default="ON") == "ON"
    mock_first_run.return_value = False
    assert locale_state("de_AT.UTF-8", default="ON") == "OFF"


# Case 5b: locale_status_in_content (Performance-Variante mit Memory-Content)
# Senior-Schaerfung SS3.4a: extract aus locale_status fuer DRY-Hygiene.
def test_locale_status_in_content():
    content = (
        "de_AT.UTF-8 UTF-8\n"
        "# de_DE.UTF-8 UTF-8\n"
    )
    assert locale_status_in_content(content, "de_AT.UTF-8") == "ACTIVE"
    assert locale_status_in_content(content, "de_DE.UTF-8") == "DISABLED"
    assert locale_status_in_content(content, "fr_FR.UTF-8") == "ABSENT"
    assert locale_status_in_content("", "de_AT.UTF-8") == "ABSENT"


# Case 5: current_default_locale liest LANG= (un-quoted, quoted, missing-file)
def test_current_default_locale(tmp_path):
    locale_file = tmp_path / "locale"
    locale_file.write_text("LANG=de_AT.UTF-8\nLC_ALL=\n")
    assert current_default_locale(default_locale_file=locale_file) == "de_AT.UTF-8"
    # Quoted Variante
    locale_file.write_text('LANG="en_US.UTF-8"\n')
    assert current_default_locale(default_locale_file=locale_file) == "en_US.UTF-8"
    # File fehlt -> None
    assert current_default_locale(default_locale_file=tmp_path / "missing") is None
