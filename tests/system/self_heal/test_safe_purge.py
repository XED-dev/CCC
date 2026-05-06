"""Tests für ccc.system.self_heal.safe_purge — 6 Cases.

Pilot-Tests für Sub-Sprint 1 (Refactor v0.9.0). Mock-Strategie:
subprocess.run wird gepatched, realistische apt-get purge --simulate
Output-Strings im `Remv <pkg> [version]`-Format.

Senior-Schärfung 2026-05-06: 6. Case `whitelist=None` für API-Symmetrie.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from ccc.system.self_heal.constants import CRITICAL_PACKAGES_WHITELIST
from ccc.system.self_heal.safe_purge import safe_purge


def _mock_simulate(remv_pkgs: list[str], returncode: int = 0) -> MagicMock:
    """Erzeugt einen subprocess.run Mock-Result für apt-get purge --simulate.

    Format: `Remv <pkgname> [<version>]` pro Zeile (echtes apt-Output-Format).
    """
    output_lines = [f"Remv {pkg} [1.0.0]" for pkg in remv_pkgs]
    result = MagicMock()
    result.returncode = returncode
    result.stdout = "\n".join(output_lines) + ("\n" if output_lines else "")
    return result


# Case 1: Cascade ohne whitelist-Treffer → Purge wird ausgeführt
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_cleared_cascade_purges(mock_run):
    mock_run.side_effect = [
        _mock_simulate(["firefox", "thunderbird"]),  # simulate
        MagicMock(returncode=0),                      # actual purge
    ]
    assert safe_purge(["firefox", "thunderbird"], whitelist=CRITICAL_PACKAGES_WHITELIST) is True
    assert mock_run.call_count == 2
    # Zweiter call ist der echte Purge mit korrekten args
    actual_purge_argv = mock_run.call_args_list[1].args[0]
    assert actual_purge_argv[:3] == ["apt-get", "purge", "-y"]
    assert "firefox" in actual_purge_argv
    assert "thunderbird" in actual_purge_argv


# Case 2: Cascade enthält whitelist-Paket → Abort, kein Purge
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_whitelist_hit_aborts(mock_run, caplog):
    mock_run.return_value = _mock_simulate(["firefox", "vanilla-gnome-desktop"])
    with caplog.at_level(logging.ERROR):
        result = safe_purge(["firefox"], whitelist=CRITICAL_PACKAGES_WHITELIST)
    assert result is False
    # Nur EIN call (simulate), kein echter Purge
    assert mock_run.call_count == 1
    assert any("ABORT safe_purge" in record.message for record in caplog.records)
    assert any("vanilla-gnome-desktop" in record.message for record in caplog.records)


# Case 3: Leere Paket-Liste → no-op, kein subprocess-Aufruf
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_empty_packages_noop(mock_run):
    assert safe_purge([], whitelist=CRITICAL_PACKAGES_WHITELIST) is True
    assert mock_run.call_count == 0


# Case 4: apt-get --simulate scheitert (returncode != 0, leerer stdout) →
# Cascade ist leer → kein whitelist-Treffer → echter Purge wird tolerant probiert
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_apt_simulate_fail_tolerated(mock_run):
    fail_sim = MagicMock(returncode=100, stdout="")
    mock_run.side_effect = [fail_sim, MagicMock(returncode=0)]
    assert safe_purge(["nonexistent-pkg"], whitelist=CRITICAL_PACKAGES_WHITELIST) is True
    assert mock_run.call_count == 2  # simulate + tolerantes purge


# Case 5: Idempotenz — zweiter Aufruf bei bereits-entferntem Paket
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_idempotent_second_call(mock_run):
    # 1. Call: simulate cascaded firefox + echter purge
    # 2. Call: simulate leer (firefox bereits weg) + purge (no-op exit 0)
    mock_run.side_effect = [
        _mock_simulate(["firefox"]),  # 1st simulate
        MagicMock(returncode=0),      # 1st purge
        _mock_simulate([]),           # 2nd simulate (leere cascade)
        MagicMock(returncode=0),      # 2nd purge (no-op)
    ]
    assert safe_purge(["firefox"], whitelist=CRITICAL_PACKAGES_WHITELIST) is True
    assert safe_purge(["firefox"], whitelist=CRITICAL_PACKAGES_WHITELIST) is True
    assert mock_run.call_count == 4


# Case 6: whitelist=None Default-Fall (API-Symmetrie, Senior-Schärfung)
# → kein Cascade-Schutz aktiv, purge wird ausgeführt egal was in Cascade ist
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_whitelist_none_default_purges(mock_run):
    mock_run.side_effect = [
        _mock_simulate(["firefox", "vanilla-gnome-desktop"]),  # cascade hat critical
        MagicMock(returncode=0),
    ]
    # whitelist nicht uebergeben = None Default
    assert safe_purge(["firefox"]) is True
    assert mock_run.call_count == 2  # simulate + echter Purge trotz critical in cascade


# Case 7: DEBIAN_FRONTEND=noninteractive in env aller subprocess-Aufrufe
# Schritt-0-Nachzieh (REFACTOR §11 Code-Backlog) — Symmetrie zu dpkg.py
# Case 6, plus stdin=DEVNULL beim purge-Apply (Bash </dev/null-Pendant).
@patch("ccc.system.self_heal.safe_purge.subprocess.run")
def test_debian_frontend_set_in_env(mock_run):
    import subprocess
    mock_run.side_effect = [
        _mock_simulate(["snapd"]),    # simulate
        MagicMock(returncode=0),      # actual purge
    ]
    safe_purge(["snapd"], whitelist=["vanilla-gnome-desktop"])
    assert mock_run.call_count == 2
    for call in mock_run.call_args_list:
        env = call.kwargs.get("env")
        assert env is not None, f"env=None bei call {call}"
        assert env.get("DEBIAN_FRONTEND") == "noninteractive", (
            f"DEBIAN_FRONTEND={env.get('DEBIAN_FRONTEND')!r}"
        )
    # Bonus-Assertion: purge-Apply hat stdin=DEVNULL (Bash </dev/null-Pendant)
    purge_call = mock_run.call_args_list[1]
    assert purge_call.kwargs.get("stdin") == subprocess.DEVNULL
