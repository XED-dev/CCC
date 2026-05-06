"""editor — apply_editor Phase-Funktion.

Migriert aus firstboot.sh v0.8.4 apply_editor (Z845-855):
EDITOR=nano in /etc/environment sicherstellen, idempotent (kein Append
wenn ^EDITOR=-Zeile schon existiert). Sub-Sprint 3.4c (Reserve-Split aus
SS3.4 weil thematisch nicht-apt-passend in apt.py-Cluster).
"""

from __future__ import annotations

import logging
from pathlib import Path

ENVIRONMENT_FILE = Path("/etc/environment")


def apply_editor(
    environment_file: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Setzt EDITOR=nano in /etc/environment falls noch nicht gesetzt.

    Idempotent: kein Append wenn ^EDITOR=-Zeile schon existiert.
    write_text auf existing file ist no-deletion-konform (kein expliziter
    unlink-Call, atomic-overwrite via Filesystem-Mainstream).
    """
    log = logger or logging.getLogger(__name__)
    path = environment_file or ENVIRONMENT_FILE

    log.info("EDITOR=nano in /etc/environment sicherstellen...")

    content = path.read_text(encoding="utf-8") if path.is_file() else ""
    for line in content.splitlines():
        if line.startswith("EDITOR="):
            log.info("  bereits vorhanden: %s — kein Append.", line)
            return

    if content and not content.endswith("\n"):
        content += "\n"
    content += "EDITOR=nano\n"
    path.write_text(content, encoding="utf-8")
    log.info("  EDITOR=nano hinzugefuegt.")
