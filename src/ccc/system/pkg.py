"""pkg — dpkg-query + locale-gen Status-Helper fuer Whiptail-Pre-Select.

Migriert aus firstboot.sh v0.8.4: pkg_is_installed, locale_is_active,
locale_status, pkg_state, locale_state, current_default_locale.

Drei-wertige Idempotenz-Logik (siehe feedback_idempotenz_first_run_vs_rerun.md):
- locale_status: ACTIVE / DISABLED / ABSENT
- pkg_state / locale_state: ON / OFF mit first-run-Default-Fallback

Bausteine fuer SS3.4 phases-Funktionen (apply_locales, apply_packages) —
drei-wertige Pre-Select bestimmt Whiptail-Default-States.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ccc.system.marker import is_first_run

LOCALE_GEN_PATH = Path("/etc/locale.gen")
DEFAULT_LOCALE_PATH = Path("/etc/default/locale")


def is_installed(name: str) -> bool:
    """True wenn dpkg-query 'install ok installed' Status zurueckgibt."""
    result = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", name],
        check=False,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0 and "install ok installed" in result.stdout


def locale_status_in_content(content: str, loc: str) -> str:
    """Drei-wertige Status (ACTIVE/DISABLED/ABSENT) in geladenem locale.gen-Content.

    Performance-Variante fuer Caller die den File-Inhalt schon im Memory haben
    (z.B. apply_locales-Diff-Logik: einmal lesen, mehrfach status-checken).
    """
    pattern = re.escape(loc)
    if re.search(rf"^[ \t]*{pattern}[ \t]+UTF-8", content, re.MULTILINE):
        return "ACTIVE"
    if re.search(rf"^#[ \t]*{pattern}[ \t]+UTF-8", content, re.MULTILINE):
        return "DISABLED"
    return "ABSENT"


def locale_status(loc: str, locale_gen: Path | None = None) -> str:
    """Drei-wertige Status (ACTIVE/DISABLED/ABSENT) in /etc/locale.gen.

    Datei-basierte Variante — delegiert an locale_status_in_content nach
    File-Read. ABSENT wenn File fehlt.
    """
    path = locale_gen or LOCALE_GEN_PATH
    if not path.is_file():
        return "ABSENT"
    return locale_status_in_content(path.read_text(encoding="utf-8"), loc)


def pkg_state(name: str, default: str = "OFF") -> str:
    """Drei-wertige Whiptail-Pre-Select fuer Pakete.
    INSTALLED -> ON. NOT-INSTALLED + first_run -> default. Sonst -> OFF.
    """
    if is_installed(name):
        return "ON"
    if is_first_run():
        return default
    return "OFF"


def locale_state(loc: str, default: str = "OFF") -> str:
    """Drei-wertige Whiptail-Pre-Select fuer Locales analog pkg_state."""
    status = locale_status(loc)
    if status == "ACTIVE":
        return "ON"
    if status == "DISABLED":
        return "OFF"
    # ABSENT: first-run-Fallback
    if is_first_run():
        return default
    return "OFF"


def current_default_locale(default_locale_file: Path | None = None) -> str | None:
    """Liest LANG= aus /etc/default/locale. None wenn File fehlt."""
    path = default_locale_file or DEFAULT_LOCALE_PATH
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("LANG="):
            value = line.split("=", 1)[1].strip()
            return value.strip("\"'")
    return None
