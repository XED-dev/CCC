"""safe_purge — apt-get purge mit Cascade-Schutz via --simulate + Whitelist.

Pattern: simuliert den Purge, parst die `Remv`-Cascade, prüft gegen
Whitelist, purgt nur bei sauberer Cascade. Verhindert dass `apt-get purge`
durch Hard-Deps system-kritische Meta-Pakete mit-reißt (siehe
firstboot.sh v0.8.2 Cascade-Vorfall, AI036-Lehre 2026-05-06).

Identisch zur Bash-Funktion `safe_purge()` in firstboot.sh v0.8.4
(Zeilen 882-905), aber Python-importierbar von ccc-Rollen + cca-Apps.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import Sequence

# Parst `Remv <pkgname> [version]`-Zeilen aus apt-get purge --simulate.
REMV_PATTERN = re.compile(r"^Remv\s+(\S+)", re.MULTILINE)


def safe_purge(
    packages: Sequence[str],
    whitelist: Sequence[str] | None = None,
    logger: logging.Logger | None = None,
) -> bool:
    """apt-get purge mit Cascade-Schutz.

    Drei Schritte:
    1. Simuliert den Purge via `apt-get purge --simulate -y <packages>`.
    2. Parst `Remv`-Zeilen → Liste aller Pakete die mit-entfernt würden.
    3. Prüft jedes whitelist-Paket gegen die Cascade-Liste.
       - Bei Treffer: ERROR-Log + return False (kein Purge).
       - Sonst: echter Purge via `apt-get purge -y -qq <packages>`.

    Args:
        packages: Pakete, die entfernt werden sollen (Sequence von Namen).
        whitelist: Pakete, die niemals durch Cascade entfernt werden dürfen.
            None = kein Cascade-Schutz aktiv (Default-Fall, vorsichtig nutzen).
        logger: Optional. Default: Modul-Logger.

    Returns:
        True wenn Purge ausgeführt wurde (oder Paket-Liste leer = no-op).
        False wenn whitelist-Treffer → Abort, kein Purge.
    """
    log = logger or logging.getLogger(__name__)

    if not packages:
        return True  # no-op

    pkgs = list(packages)

    # Self-Heal non-interactive — analog dpkg.py-Composite (cca-Standalone hat
    # keinen Bash-Wrapper-Erbe). Schritt-0-Nachzieh REFACTOR §11.
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

    sim = subprocess.run(
        ["apt-get", "purge", "--simulate", "-y", *pkgs],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )
    cascade = REMV_PATTERN.findall(sim.stdout)

    if whitelist:
        whitelist_set = set(whitelist)
        hits = [pkg for pkg in cascade if pkg in whitelist_set]
        if hits:
            log.error(
                "ABORT safe_purge: cascade entfernt kritische Pakete: %s",
                ", ".join(hits),
            )
            log.error("  Vollstaendige Cascade: %s", ", ".join(cascade) or "leer")
            log.error(
                "  Skript-Fix noetig: Paket-Liste reduzieren ODER Whitelist anpassen."
            )
            log.error(
                "  Recovery: kein automatischer Purge, %s bleibt installiert.",
                ", ".join(pkgs),
            )
            return False

    log.info("safe_purge cleared (cascade: %s)", ", ".join(cascade) or "leer")

    subprocess.run(
        ["apt-get", "purge", "-y", "-qq", *pkgs],
        check=False,
        env=env,
        stdin=subprocess.DEVNULL,  # configfile-Diff-Prompt-Schutz (Bash </dev/null)
    )
    return True
