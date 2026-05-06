"""Tests fuer ccc.system.whiptail — 4 Cases."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ccc.system.whiptail import checklist, menu, msgbox, yesno


# Case 1: msgbox returns returncode + Args-Check
@patch("ccc.system.whiptail.subprocess.run")
def test_msgbox_returns_returncode(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert msgbox("Title", "Hello") == 0
    call_args = mock_run.call_args.args[0]
    assert call_args[:5] == ["whiptail", "--title", "Title", "--msgbox", "Hello"]


# Case 2: yesno True/False (rc=0/rc=1/rc=255)
@patch("ccc.system.whiptail.subprocess.run")
def test_yesno_true_false(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    assert yesno("T", "?") is True
    mock_run.return_value = MagicMock(returncode=1)
    assert yesno("T", "?") is False
    mock_run.return_value = MagicMock(returncode=255)  # ESC
    assert yesno("T", "?") is False


# Case 3: menu returns (returncode, selected_tag) aus stderr
@patch("ccc.system.whiptail.subprocess.run")
def test_menu_returns_selected_tag(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="UTC\n")
    rc, selected = menu(
        "TZ", "Wahl?",
        items=[("UTC", "default"), ("Europe/Vienna", "DACH")],
    )
    assert rc == 0
    assert selected == "UTC"
    # Cancel-Pfad: returncode != 0, stderr leer
    mock_run.return_value = MagicMock(returncode=1, stderr="")
    rc, selected = menu("TZ", "Wahl?", items=[("UTC", "default")])
    assert rc == 1
    assert selected == ""


# Case 4: checklist parst quoted Tags + Cancel-Pfad
@patch("ccc.system.whiptail.subprocess.run")
def test_checklist_parses_quoted_tags(mock_run):
    # Happy-Path: zwei Locales gewaehlt
    mock_run.return_value = MagicMock(
        returncode=0, stderr='"de_AT.UTF-8" "en_US.UTF-8"',
    )
    rc, selected = checklist(
        "Locales", "Wahl",
        items=[
            ("de_AT.UTF-8", "AT", "ON"),
            ("en_US.UTF-8", "US", "OFF"),
        ],
    )
    assert rc == 0
    assert selected == ["de_AT.UTF-8", "en_US.UTF-8"]
    # Cancel-Pfad: returncode != 0 -> []
    mock_run.return_value = MagicMock(returncode=1, stderr="")
    rc, selected = checklist("Locales", "Wahl", items=[("a", "A", "ON")])
    assert rc == 1
    assert selected == []
