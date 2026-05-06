"""dpkg — Self-Heal-Composite (snap-purge + dpkg-cfg + apt-fix + autoremove).

Vier Schritte (Toleranz-Asymmetrie analog Bash-Original):
  1. safe_purge(snap_redirect_packages, whitelist)  — TOLERANT (return False ok)
  2. dpkg --configure -a                            — TOLERANT (vielleicht keine halben Pakete)
  3. apt-get install -f -y -qq                      — STRICT (broken-deps muss fixen)
  4. apt-get autoremove --purge -y -qq              — STRICT (state-inkonsistent sonst)

Schritte 1+2 sind „vielleicht-helfen" — duerfen scheitern.
Schritte 3+4 sind „muss-funktionieren" — bei Fehler wird subprocess.CalledProcessError
propagiert (Caller entscheidet ueber Recovery-Strategie).

stdin=DEVNULL bei Schritten 3+4 verhindert configfile-Diff-Prompts (Bash-1:1
zu </dev/null). stderr=DEVNULL bei Schritt 2 schluckt dpkg-stderr-Noise auf
sauberem System (Bash-1:1 zu 2>/dev/null).

Source: firstboot.sh v0.8.4 self_heal_dpkg() (Zeilen 934-946).

Caller-Beispiel (cca/apps/gnome.py Sub-Sprint 2 Modul #5):
    from ccc.system.self_heal import self_heal_dpkg
    self_heal_dpkg()  # Defaults aus constants.py
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Sequence

from ccc.system.self_heal.constants import (
    CRITICAL_PACKAGES_WHITELIST,
    SNAP_REDIRECT_PACKAGES,
)
from ccc.system.self_heal.safe_purge import safe_purge


def self_heal_dpkg(
    snap_redirect_packages: Sequence[str] = SNAP_REDIRECT_PACKAGES,
    whitelist: Sequence[str] = CRITICAL_PACKAGES_WHITELIST,
    logger: logging.Logger | None = None,
) -> None:
    """Self-Heal-Pre-Phase fuer dpkg/apt — Composite aus vier Schritten.

    Idempotent: alle Schritte sind no-op auf sauberem System.
    Bei Schritten 3+4 wird subprocess.CalledProcessError propagiert.
    """
    log = logger or logging.getLogger(__name__)

    # Self-Heal soll non-interactive laufen (cca-Standalone-Path hat keinen
    # Bash-Wrapper, der DEBIAN_FRONTEND global setzen wuerde — Bash-firstboot
    # Z40 hat das per `export`, hier per env-dict pro subprocess).
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

    # 1. snap-Redirect-Pakete entfernen mit Cascade-Schutz
    log.info("self_heal_dpkg: safe_purge snap-Redirect-Pakete")
    if not safe_purge(snap_redirect_packages, whitelist=whitelist, logger=log):
        # safe_purge loggt bereits ERROR-Volldump (Cascade + Recovery-Hinweis).
        # Composite-Warning klaert Caller-Sicht: warum wir trotz abort weitermachen.
        log.warning(
            "self_heal_dpkg: safe_purge abort, snap-Redirect bleibt installiert — "
            "apt-fix-Schritte (3+4) muessen damit umgehen"
        )

    # 2. dpkg --configure -a (tolerant — finalisiert halb-konfigurierte Pakete)
    # stderr=DEVNULL: schluckt dpkg-Noise auf sauberem System (Bash 2>/dev/null)
    log.info("self_heal_dpkg: dpkg --configure -a")
    subprocess.run(
        ["dpkg", "--configure", "-a"],
        check=False,
        env=env,
        stderr=subprocess.DEVNULL,
    )

    # 3. apt-get install -f -y -qq (STRICT — broken-deps muss fixen)
    # stdin=DEVNULL: verhindert configfile-Diff-Prompts (Bash </dev/null)
    log.info("self_heal_dpkg: apt-get install -f -y -qq")
    subprocess.run(
        ["apt-get", "install", "-f", "-y", "-qq"],
        check=True,
        env=env,
        stdin=subprocess.DEVNULL,
    )

    # 4. apt-get autoremove --purge -y -qq (STRICT — orphans + locale-Pakete)
    # stdin=DEVNULL: verhindert configfile-Diff-Prompts (Bash </dev/null)
    log.info("self_heal_dpkg: apt-get autoremove --purge -y -qq")
    subprocess.run(
        ["apt-get", "autoremove", "--purge", "-y", "-qq"],
        check=True,
        env=env,
        stdin=subprocess.DEVNULL,
    )
