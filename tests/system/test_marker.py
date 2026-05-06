"""Tests fuer ccc.system.marker — 3 Cases."""

from __future__ import annotations

from ccc.system.marker import is_first_run, set_first_run_done


# Case 1: Marker fehlt → is_first_run = True
def test_is_first_run_when_marker_absent(tmp_path):
    marker = tmp_path / "subdir" / "firstboot.applied"
    assert is_first_run(marker=marker) is True


# Case 2: set_first_run_done erstellt Marker → is_first_run = False
def test_is_first_run_after_set_done(tmp_path):
    marker = tmp_path / "subdir" / "firstboot.applied"
    set_first_run_done(marker=marker)
    assert marker.exists()
    assert is_first_run(marker=marker) is False


# Case 3: set_first_run_done ist idempotent (zweimal = no-op, Bash-touch-konform)
def test_set_first_run_done_idempotent(tmp_path):
    marker = tmp_path / "firstboot.applied"
    set_first_run_done(marker=marker)
    assert marker.exists()
    set_first_run_done(marker=marker)  # zweiter Aufruf
    assert marker.exists()
    # touch() updatet mtime — beide Aufrufe schreiben Marker neu, kein Crash
