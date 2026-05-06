"""pro_notice — non-destruktive Ubuntu-Pro-Werbung-Deaktivierung.

Drei Schritte (alle idempotent + reversibel via mv-Pattern):
  A) pro config set apt_news=false  (offizieller Pfad ab Pro-Client v30)
  B) ESM-APT-Hook 20apt-esm-hook.conf -> .bak (mv, no-deletion-konform)
  C) systemctl disable --now apt-news.service (wenn vorhanden)

Lehre: AI036-Cascade-Vorfall 2026-05-06 — destructive Pro-Client-Purge
hat Cascade-Removes ausgeloest. Diese Funktion ist die non-destruktive
Mainstream-Variante (Memory: feedback_tool_cli_help_first.md Anhang
2026-05-06).

Source: firstboot.sh v0.8.4 self_heal_pro_notice() (Zeilen 910-928).

Scope-Anker (Senior-Konsens AI036+AI037 2026-05-06):
- MOTD-Layer (/etc/update-motd.d/91-contract-ua-esm-status + motd-news.service)
  ist OUT-OF-SCOPE in v0.9.0. Apt-Layer-Direktive ist Geltungsbereich.
- Hook-Reinstall-Edge-Case: vanilla-gnome-desktop-Recommends koennen
  ubuntu-pro-client wieder reinziehen, ESM-Hook kommt als Original zurueck.
  pro-config-Persistenz in /var/lib/ubuntu-advantage/ dominiert dann —
  Werbung bleibt deaktiviert. Self-Heal-Re-Run-Pattern faengt den Hook beim
  naechsten Lauf wieder ab. Eventually-consistent-Idempotenz ist scharf
  genug.
- .bak-Overwrite-Edge-Case: Bash-1:1 gespiegelt, KEIN Timestamp-Suffix
  (.bak.<ts> wie migrate_old_symlink). KISS gewinnt — extrem schmaler
  Edge-Case (manueller Operator-Eingriff zwischen zwei Self-Heal-Laeufen).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

ESM_HOOK_PATH = Path("/etc/apt/apt.conf.d/20apt-esm-hook.conf")


def disable_pro_notice(
    logger: logging.Logger | None = None,
    esm_hook: Path | None = None,
) -> None:
    """Ubuntu-Pro-Werbung non-destruktiv deaktivieren (drei Schritte).

    Idempotent: alle Schritte sind tolerant — pro-CLI darf fehlen,
    ESM-Hook darf bereits umbenannt sein, Service darf nicht installiert
    sein. Kein Crash bei erneutem Aufruf.
    """
    log = logger or logging.getLogger(__name__)
    hook = esm_hook or ESM_HOOK_PATH
    backup = hook.with_suffix(hook.suffix + ".bak")

    # A) pro CLI (offizieller Pfad ab Pro-Client v30)
    # apt_news=false wird persistent in /var/lib/ubuntu-advantage/ gespeichert,
    # ueberlebt apt-Reinstall des Pakets selbst. Daher dominante Quelle
    # gegenueber B+C, die nur File-/Service-State manipulieren.
    if shutil.which("pro"):
        log.info("disable_pro_notice: pro config set apt_news=false")
        subprocess.run(
            ["pro", "config", "set", "apt_news=false"],
            check=False, text=True, capture_output=True,
        )

    # B) ESM-APT-Hook -> .bak (no-deletion-konform, reversibel)
    if hook.is_file():
        log.info("disable_pro_notice: %s -> %s", hook.name, backup.name)
        hook.rename(backup)

    # C) apt-news.service deaktivieren wenn vorhanden
    # Unconditional + tolerant: deckt drei Faelle ab —
    #   (1) Pro-Client-Versions-Drift v25 vs v30+ (apt_news=false ist v30+-Pfad,
    #       greift auf aelteren Boxen nicht zuverlaessig)
    #   (2) Service kann von update-notifier-common kommen, nicht nur von
    #       ubuntu-pro-client
    #   (3) systemctl disable <not-installed> ist toleriert via capture_output
    log.info("disable_pro_notice: systemctl disable --now apt-news.service")
    subprocess.run(
        ["systemctl", "disable", "--now", "apt-news.service"],
        check=False, text=True, capture_output=True,
    )
