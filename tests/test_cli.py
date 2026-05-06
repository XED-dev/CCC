"""Smoke-Tests fuer ccc.cli — 2 Cases (SS3.6 Integration)."""

from __future__ import annotations

from typer.testing import CliRunner

from ccc.cli import app

runner = CliRunner()


def test_cli_app_registered_commands():
    """ccc.cli.app laedt + alle erwarteten Verben sind registriert."""
    assert app is not None
    command_names = {cmd.name for cmd in app.registered_commands}
    assert "list" in command_names
    assert "create" in command_names
    assert "menu" in command_names
    assert "bootstrap-system" in command_names


def test_bootstrap_system_help_works():
    """ccc bootstrap-system --help gibt Help-Text + erwartete Args."""
    result = runner.invoke(app, ["bootstrap-system", "--help"])
    assert result.exit_code == 0
    # Help-Text sollte die wichtigsten Args erwaehnen
    assert "--lang" in result.output
    assert "--tz" in result.output
    assert "--locales" in result.output
