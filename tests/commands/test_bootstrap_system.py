"""Tests fuer ccc.commands.bootstrap_system — 5 Cases.

Test 1: non-interactive Verb-Composition (alle apply_*-Funktionen aufgerufen).
Tests 2-5: State-Machine Phase-Loop-Coverage:
  Test 2 — Happy-Path: alle 6 Phasen Yes -> return inputs-Dict
  Test 3 — Cancel Phase 1 -> Abort-Confirm True -> return None
  Test 4 — Back-Button Phase 3 -> Phase decrement
  Test 5 — Re-Prompt Phase 3 (leere Locales) -> continue (kein decrement)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ccc.commands.bootstrap_system import _collect_inputs_interactive, bootstrap_system


# Case 1: non-interactive Verb-Composition (alle 5 apply_*-Phasen aufgerufen)
@patch("ccc.commands.bootstrap_system.set_first_run_done")
@patch("ccc.commands.bootstrap_system.apply_editor")
@patch("ccc.commands.bootstrap_system.apply_dist_upgrade")
@patch("ccc.commands.bootstrap_system.apply_packages")
@patch("ccc.commands.bootstrap_system.apply_locales")
@patch("ccc.commands.bootstrap_system.apply_timezone")
@patch("ccc.commands.bootstrap_system.disable_pro_notice")
@patch("ccc.commands.bootstrap_system.self_heal_dpkg")
@patch("ccc.commands.bootstrap_system.init_audit_log")
@patch("ccc.commands.bootstrap_system.sys.stdin")
def test_non_interactive_happy_path(
    mock_stdin, mock_log_init, mock_dpkg, mock_pro,
    mock_tz, mock_loc, mock_pkg, mock_du, mock_ed, mock_marker,
):
    mock_stdin.isatty.return_value = False
    mock_log_init.return_value = MagicMock()
    bootstrap_system(
        lang="DE", tz="UTC",
        locales="de_AT.UTF-8", default_locale="de_AT.UTF-8",
        pkgs="htop curl",
        remove_deselected=False, dist_upgrade=False,
    )
    mock_dpkg.assert_called_once()
    mock_pro.assert_called_once()
    assert mock_tz.call_args.args[0] == "UTC"
    mock_loc.assert_called_once()
    mock_pkg.assert_called_once()
    mock_du.assert_called_once()
    mock_ed.assert_called_once()
    mock_marker.assert_called_once()


# Case 2: State-Machine Happy-Path — alle 6 Phasen Yes -> return inputs-Dict
@patch("ccc.commands.bootstrap_system.pkg_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.locale_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.whiptail")
def test_state_machine_happy_path(mock_wt, mock_loc_state, mock_pkg_state):
    # Phase 1: menu Sprache -> "DE"
    # Phase 2: menu TZ -> "UTC"
    # Phase 3: checklist Locales -> ["de_AT.UTF-8"]
    # Phase 4: menu Default-Locale -> "de_AT.UTF-8"
    # Phase 5: checklist Pkgs -> ["htop"]
    # Phase 6: yesno Confirm -> True
    mock_wt.menu.side_effect = [
        (0, "DE"),                # Phase 1
        (0, "UTC"),               # Phase 2
        (0, "de_AT.UTF-8"),       # Phase 4
    ]
    mock_wt.checklist.side_effect = [
        (0, ["de_AT.UTF-8"]),     # Phase 3
        (0, ["htop"]),            # Phase 5
    ]
    mock_wt.yesno.return_value = True  # Phase 6 Confirm

    result = _collect_inputs_interactive()
    assert result is not None
    assert result["lang"] == "DE"
    assert result["tz"] == "UTC"
    assert result["locales"] == ["de_AT.UTF-8"]
    assert result["default_locale"] == "de_AT.UTF-8"
    assert result["pkgs"] == ["htop"]


# Case 3: Cancel in Phase 1 (Sprache) -> Abort-Confirm True -> return None
@patch("ccc.commands.bootstrap_system.whiptail")
def test_state_machine_cancel_phase_1_aborts(mock_wt):
    # Phase 1 Sprache: rc=1 (Cancel) -> Abort-Yesno True -> return None
    mock_wt.menu.return_value = (1, "")  # rc=1 (cancel)
    mock_wt.yesno.return_value = True    # Abort-Confirm = Yes

    result = _collect_inputs_interactive()
    assert result is None
    # Sprache-Menu wurde 1× aufgerufen, dann Abort-Yesno
    assert mock_wt.menu.call_count == 1
    assert mock_wt.yesno.call_count == 1


# Case 4: Back-Button Phase 3 -> Phase decrement (3 -> 2 -> 3 wieder)
@patch("ccc.commands.bootstrap_system.pkg_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.locale_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.whiptail")
def test_state_machine_back_button_phase_3(mock_wt, mock_loc_state, mock_pkg_state):
    # Phase 1+2 ok, Phase 3 cancel (rc=1) -> Phase 2 wieder ok ->
    # Phase 3 ok -> Phase 4+5+6 ok
    mock_wt.menu.side_effect = [
        (0, "DE"),                # Phase 1
        (0, "UTC"),               # Phase 2 (1. Mal)
        (0, "Europe/Vienna"),     # Phase 2 (2. Mal nach Back)
        (0, "de_AT.UTF-8"),       # Phase 4
    ]
    mock_wt.checklist.side_effect = [
        (1, []),                  # Phase 3 (1. Mal): Cancel
        (0, ["de_AT.UTF-8"]),     # Phase 3 (2. Mal nach Back): ok
        (0, ["htop"]),            # Phase 5
    ]
    mock_wt.yesno.return_value = True  # Phase 6

    result = _collect_inputs_interactive()
    assert result is not None
    assert result["tz"] == "Europe/Vienna"  # zweite Phase-2-Wahl
    # Phase-2-Menu wurde 2x aufgerufen (vor + nach Back)
    assert mock_wt.menu.call_count == 4  # P1 + P2 + P2-redo + P4


# Case 5: Re-Prompt Phase 3 (leere Locales) -> continue (kein decrement)
@patch("ccc.commands.bootstrap_system.pkg_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.locale_state", return_value="ON")
@patch("ccc.commands.bootstrap_system.whiptail")
def test_state_machine_reprompt_empty_locales(mock_wt, mock_loc_state, mock_pkg_state):
    # Phase 3 (1. Mal): rc=0 aber val=[] -> msgbox + continue
    # Phase 3 (2. Mal): rc=0 + val nicht leer -> phase=4
    mock_wt.menu.side_effect = [
        (0, "DE"),                # Phase 1
        (0, "UTC"),               # Phase 2
        (0, "de_AT.UTF-8"),       # Phase 4
    ]
    mock_wt.checklist.side_effect = [
        (0, []),                  # Phase 3 (1. Mal): leere Auswahl
        (0, ["de_AT.UTF-8"]),     # Phase 3 (2. Mal): nicht leer
        (0, ["htop"]),            # Phase 5
    ]
    mock_wt.msgbox.return_value = 0
    mock_wt.yesno.return_value = True  # Phase 6

    result = _collect_inputs_interactive()
    assert result is not None
    # msgbox wurde 1x aufgerufen (leere Locales-Warnung)
    assert mock_wt.msgbox.call_count == 1
    # Phase-3-Checklist wurde 2x aufgerufen (Re-Prompt)
    assert mock_wt.checklist.call_count == 3  # P3-empty + P3-redo + P5
