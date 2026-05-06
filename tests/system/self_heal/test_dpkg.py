"""Tests fuer ccc.system.self_heal.dpkg — 5 Cases.

Senior-Schaerfung AI037 2026-05-06: 5. Case test_dpkg_configure_fail_
continues_tolerant fuer Symmetrie zu pro_notice (Toleranz-Pfad braucht
explizit Coverage, jedes tolerante Schritt-Versagen separat).
"""

from __future__ import annotations

import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ccc.system.self_heal.dpkg import self_heal_dpkg


# Case 1: happy-path — alle vier Schritte erfolgreich
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=True)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_happy_path(mock_run, mock_safe_purge):
    self_heal_dpkg()
    # safe_purge 1× + 3 subprocess.run (dpkg --configure, apt install -f, autoremove)
    assert mock_safe_purge.call_count == 1
    assert mock_run.call_count == 3
    # Reihenfolge: dpkg --configure -a → apt install -f → apt autoremove
    assert mock_run.call_args_list[0].args[0][:2] == ["dpkg", "--configure"]
    assert mock_run.call_args_list[1].args[0][:3] == ["apt-get", "install", "-f"]
    assert mock_run.call_args_list[2].args[0][:3] == ["apt-get", "autoremove", "--purge"]


# Case 2: safe_purge whitelist-hit (returns False) → Warning, andere Schritte laufen
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=False)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_safe_purge_whitelist_hit_continues(mock_run, mock_safe_purge, caplog):
    with caplog.at_level(logging.WARNING):
        self_heal_dpkg()
    # safe_purge returns False → warning geloggt, aber dpkg/apt-Schritte laufen
    assert mock_run.call_count == 3
    assert any("safe_purge abort" in record.message for record in caplog.records)


# Case 3: apt-get install -f schlaegt fehl → CalledProcessError propagiert (STRICT)
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=True)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_apt_install_fail_propagates(mock_run, mock_safe_purge):
    mock_run.side_effect = [
        MagicMock(returncode=0),  # dpkg --configure (tolerant)
        subprocess.CalledProcessError(100, ["apt-get", "install", "-f"]),
    ]
    with pytest.raises(subprocess.CalledProcessError):
        self_heal_dpkg()
    # Schritt 4 (autoremove) wird NICHT mehr erreicht
    assert mock_run.call_count == 2


# Case 4: autoremove schlaegt fehl → CalledProcessError propagiert (STRICT)
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=True)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_autoremove_fail_propagates(mock_run, mock_safe_purge):
    mock_run.side_effect = [
        MagicMock(returncode=0),  # dpkg --configure (tolerant)
        MagicMock(returncode=0),  # apt-get install -f (ok)
        subprocess.CalledProcessError(100, ["apt-get", "autoremove", "--purge"]),
    ]
    with pytest.raises(subprocess.CalledProcessError):
        self_heal_dpkg()
    assert mock_run.call_count == 3


# Case 5: dpkg --configure -a fail (returncode != 0) → Schritt 3+4 laufen weiter
# Senior-Schaerfung AI037: Toleranz-Pfad fuer Schritt 2 braucht eigene Coverage
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=True)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_dpkg_configure_fail_continues_tolerant(mock_run, mock_safe_purge):
    mock_run.side_effect = [
        MagicMock(returncode=2),  # dpkg --configure: fail (tolerant via check=False)
        MagicMock(returncode=0),  # apt-get install -f: ok
        MagicMock(returncode=0),  # apt-get autoremove: ok
    ]
    self_heal_dpkg()  # KEIN raise erwartet
    assert mock_run.call_count == 3
    assert mock_run.call_args_list[1].args[0][:3] == ["apt-get", "install", "-f"]


# Case 6: DEBIAN_FRONTEND=noninteractive in env aller subprocess-Aufrufe
# Senior-Schaerfung AI037 (Bug-Catch nachtraeglich Modul #4): cca-Standalone-
# Path hat keinen Bash-Wrapper, der DEBIAN_FRONTEND global setzen wuerde —
# Lib muss es selbst setzen, damit configfile-Diff-Prompts blockiert werden.
@patch("ccc.system.self_heal.dpkg.safe_purge", return_value=True)
@patch("ccc.system.self_heal.dpkg.subprocess.run")
def test_debian_frontend_set_in_env(mock_run, mock_safe_purge):
    self_heal_dpkg()
    assert mock_run.call_count == 3
    for call in mock_run.call_args_list:
        env = call.kwargs.get("env")
        assert env is not None, f"env=None bei call {call}"
        assert env.get("DEBIAN_FRONTEND") == "noninteractive", (
            f"DEBIAN_FRONTEND={env.get('DEBIAN_FRONTEND')!r} bei call {call}"
        )
