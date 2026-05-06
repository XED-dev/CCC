"""Tests fuer ccc.system.self_heal.pro_notice — 5 Cases.

Senior-Schaerfung AI037 2026-05-06: 5. Case happy-path mit allen drei
Schritten aktiv (Symmetrie zu safe_purge §6 whitelist=None Default-Case).
"""

from __future__ import annotations

from unittest.mock import patch

from ccc.system.self_heal.pro_notice import disable_pro_notice


# Case 1: pro CLI nicht installiert → Schritt A wird skipped
@patch("ccc.system.self_heal.pro_notice.shutil.which", return_value=None)
@patch("ccc.system.self_heal.pro_notice.subprocess.run")
def test_pro_cli_skipped_when_pro_absent(mock_run, mock_which, tmp_path):
    fake_hook = tmp_path / "20apt-esm-hook.conf"  # File fehlt absichtlich
    disable_pro_notice(esm_hook=fake_hook)
    # Nur EIN subprocess-Aufruf: systemctl (Schritt C). Schritt A skipped.
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0][0] == "systemctl"


# Case 2: ESM-Hook existiert → wird zu .bak umbenannt (mv-Pattern)
@patch("ccc.system.self_heal.pro_notice.shutil.which", return_value=None)
@patch("ccc.system.self_heal.pro_notice.subprocess.run")
def test_esm_hook_renamed_to_bak(mock_run, mock_which, tmp_path):
    fake_hook = tmp_path / "20apt-esm-hook.conf"
    fake_hook.write_text("ESM-config")
    disable_pro_notice(esm_hook=fake_hook)
    assert not fake_hook.exists(), "Original-Hook sollte umbenannt sein"
    assert (tmp_path / "20apt-esm-hook.conf.bak").exists()


# Case 3: pro vorhanden → Schritt A wird ausgefuehrt
@patch("ccc.system.self_heal.pro_notice.shutil.which", return_value="/usr/bin/pro")
@patch("ccc.system.self_heal.pro_notice.subprocess.run")
def test_pro_called_when_present(mock_run, mock_which, tmp_path):
    fake_hook = tmp_path / "20apt-esm-hook.conf"
    disable_pro_notice(esm_hook=fake_hook)
    # Zwei subprocess-Aufrufe: pro + systemctl (kein ESM-Hook im tmp_path)
    assert mock_run.call_count == 2
    pro_args = mock_run.call_args_list[0].args[0]
    assert pro_args[:2] == ["pro", "config"]


# Case 4: Idempotenz — zweiter Aufruf nach erstem (ESM-Hook schon weg) → no crash
@patch("ccc.system.self_heal.pro_notice.shutil.which", return_value=None)
@patch("ccc.system.self_heal.pro_notice.subprocess.run")
def test_idempotent_second_call(mock_run, mock_which, tmp_path):
    fake_hook = tmp_path / "20apt-esm-hook.conf"
    fake_hook.write_text("ESM-config")
    disable_pro_notice(esm_hook=fake_hook)  # 1. Lauf: ESM-Hook -> .bak
    disable_pro_notice(esm_hook=fake_hook)  # 2. Lauf: ESM-Hook bereits weg
    # Beide Laeufe: nur systemctl (kein pro, kein ESM-Hook beim 2. Lauf)
    assert mock_run.call_count == 2  # 1× systemctl pro Lauf
    assert (tmp_path / "20apt-esm-hook.conf.bak").exists()


# Case 5: Happy-Path — pro CLI vorhanden + ESM-Hook vorhanden + systemctl
# Senior-Schaerfung AI037: canonical Happy-Path mit allen drei Schritten aktiv
@patch("ccc.system.self_heal.pro_notice.shutil.which", return_value="/usr/bin/pro")
@patch("ccc.system.self_heal.pro_notice.subprocess.run")
def test_happy_path_pro_und_hook_present(mock_run, mock_which, tmp_path):
    fake_hook = tmp_path / "20apt-esm-hook.conf"
    fake_hook.write_text("ESM-config")
    disable_pro_notice(esm_hook=fake_hook)
    # Drei Aktionen: pro + rename + systemctl (rename ist kein subprocess)
    assert mock_run.call_count == 2  # pro + systemctl
    assert mock_run.call_args_list[0].args[0][:2] == ["pro", "config"]
    assert mock_run.call_args_list[1].args[0][0] == "systemctl"
    assert not fake_hook.exists()
    assert (tmp_path / "20apt-esm-hook.conf.bak").exists()
