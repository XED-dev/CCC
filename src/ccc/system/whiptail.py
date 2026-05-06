"""whiptail — subprocess-Wrapper fuer TTY-interaktive Whiptail-Dialoge.

Vier Wrapper analog firstboot.sh-Verwendung:
  msgbox   — Info-Dialog mit OK-Button
  yesno    — Yes/No-Dialog (returncode 0=Yes, 1=No, 255=Esc)
  menu     — Single-Select-Menue (gibt gewaehlten Tag-String zurueck)
  checklist — Multi-Select-Menue (gibt Liste gewaehlter Tags zurueck)

TTY-Hybrid (Pattern aus subprocess-Doku, AI037 SS3.0-Recherche):
  - stdin=sys.stdin       (Whiptail braucht TTY-Eingabe)
  - stdout=sys.stdout      (Whiptail braucht TTY-Ausgabe)
  - stderr=subprocess.PIPE (User-Wahl wird auf stderr geschrieben, captured)

Returncode-Konvention:
  0   - OK / Yes / Auswahl bestaetigt
  1   - No / Cancel
  255 - ESC / Abbruch ohne Antwort

Migration aus firstboot.sh: alle whiptail-Calls (z.B.
collect_inputs_interactive in 6-Phasen-State-Machine) werden in SS3.4
phases-Funktionen + SS3.5 bootstrap_system Verb auf diese Wrapper umgestellt.
"""

from __future__ import annotations

import subprocess
import sys


def msgbox(title: str, text: str, height: int = 10, width: int = 60) -> int:
    """Info-Dialog mit OK-Button. Returncode 0 = OK gedrueckt."""
    return subprocess.run(
        ["whiptail", "--title", title, "--msgbox", text, str(height), str(width)],
        check=False,
    ).returncode


def yesno(title: str, text: str, height: int = 10, width: int = 60) -> bool:
    """Yes/No-Dialog. Returns True bei Yes, False bei No/Cancel/Esc."""
    rc = subprocess.run(
        ["whiptail", "--title", title, "--yesno", text, str(height), str(width)],
        check=False,
    ).returncode
    return rc == 0


def menu(
    title: str,
    prompt: str,
    items: list[tuple[str, str]],
    height: int = 18,
    width: int = 60,
    list_height: int | None = None,
) -> tuple[int, str]:
    """Single-Select-Menue. Items als Liste (tag, description).

    Returns (returncode, selected_tag). Bei Cancel/Esc returncode != 0,
    selected_tag = "".
    """
    if list_height is None:
        list_height = len(items)
    args = [
        "whiptail", "--title", title,
        "--menu", prompt, str(height), str(width), str(list_height),
    ]
    for tag, desc in items:
        args.extend([tag, desc])
    result = subprocess.run(
        args,
        check=False,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=subprocess.PIPE,
        text=True,
    )
    selected = (result.stderr or "").strip()
    return result.returncode, selected


def checklist(
    title: str,
    prompt: str,
    items: list[tuple[str, str, str]],
    height: int = 18,
    width: int = 65,
    list_height: int | None = None,
) -> tuple[int, list[str]]:
    """Multi-Select-Menue. Items als Liste (tag, description, state)
    wo state in {"ON", "OFF"}.

    Returns (returncode, selected_tags). Bei Cancel/Esc selected_tags = [].
    Whiptail gibt selected_tags space-separated mit double-quotes zurueck.
    """
    if list_height is None:
        list_height = len(items)
    args = [
        "whiptail", "--title", title,
        "--checklist", prompt, str(height), str(width), str(list_height),
    ]
    for tag, desc, state in items:
        args.extend([tag, desc, state])
    result = subprocess.run(
        args,
        check=False,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return result.returncode, []
    raw = (result.stderr or "").strip()
    # Whiptail gibt Tags space-separated mit Anfuehrungszeichen zurueck:
    # '"de_AT.UTF-8" "en_US.UTF-8"' -> wir entfernen die Anfuehrungszeichen.
    # Backlog REFACTOR §11: shlex.split() falls Tags mit Leerzeichen kommen.
    selected = [tag.strip('"') for tag in raw.split()]
    return result.returncode, selected
