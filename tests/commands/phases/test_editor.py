"""Tests fuer ccc.commands.phases.editor — 2 Cases."""

from __future__ import annotations

from ccc.commands.phases.editor import apply_editor


# Case 1: EDITOR fehlt -> wird angehaengt
def test_apply_editor_appends_when_absent(tmp_path):
    env_file = tmp_path / "environment"
    env_file.write_text("PATH=/usr/local/bin:/usr/bin\n")
    apply_editor(environment_file=env_file)
    content = env_file.read_text()
    assert "PATH=/usr/local/bin:/usr/bin" in content  # bestehender Inhalt bleibt
    assert "EDITOR=nano" in content


# Case 2: EDITOR bereits gesetzt -> kein Append (idempotent)
def test_apply_editor_skips_when_present(tmp_path):
    env_file = tmp_path / "environment"
    env_file.write_text("EDITOR=vim\nPATH=/usr/bin\n")
    apply_editor(environment_file=env_file)
    content = env_file.read_text()
    # Kein zweiter EDITOR=-Eintrag (count=1)
    assert content.count("EDITOR=") == 1
    # Original-Wert (vim) bleibt unangetastet
    assert "EDITOR=vim" in content
    assert "EDITOR=nano" not in content
