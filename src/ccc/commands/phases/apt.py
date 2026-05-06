"""apt — apply_packages + apply_dist_upgrade Phase-Funktionen.

Migriert aus firstboot.sh v0.8.4 apply_packages (Z733-796) +
apply_dist_upgrade_prompt (Z800-841).

apply_packages: Diff-Logik to_install/to_remove + apt-get install/remove.
                Remove-Phase nur mit User-Confirmation (interactive: whiptail-
                yesno, non-interactive: remove_deselected-Flag).

apply_dist_upgrade: apt list --upgradable + count -> falls Updates ->
                    Yesno-Confirm -> apt-get dist-upgrade + autoremove + autoclean.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Sequence

from ccc.system import whiptail
from ccc.system.i18n import t
from ccc.system.pkg import is_installed

# Pakete die im Whiptail-Menue angeboten werden — bei deselect=remove-Diff
# nur diese Pakete werden zur Deinstallation vorgeschlagen (Schutzschicht
# gegen versehentliche System-Paket-Deinstallation).
PKG_MENU_LIST: tuple[str, ...] = (
    "htop", "curl", "wget", "sudo", "psmisc", "net-tools",
    "iproute2", "iputils-ping", "gnupg", "nano", "pwgen", "socat",
)


def apply_packages(
    packages: Sequence[str],
    interactive: bool = False,
    remove_deselected: bool = False,
    lang: str = "DE",
    logger: logging.Logger | None = None,
    menu_list: Sequence[str] = PKG_MENU_LIST,
) -> None:
    """Diff-Logik to_install/to_remove + apt-get install/remove.

    Remove-Phase erfordert User-Confirmation:
      interactive=True  -> whiptail.yesno-Dialog
      interactive=False + remove_deselected=True -> ENV-Override
      sonst -> kein Remove (User-Wille uneindeutig, sicherer Default)
    """
    log = logger or logging.getLogger(__name__)
    pkgs_set = set(packages)

    to_install = [p for p in packages if not is_installed(p)]
    to_remove = [p for p in menu_list if is_installed(p) and p not in pkgs_set]

    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

    # Install-Phase (STRICT)
    if to_install:
        log.info(
            "Pakete installieren (--no-install-recommends): %s",
            " ".join(to_install),
        )
        subprocess.run(
            ["apt-get", "install", "-y", "-qq", "--no-install-recommends", *to_install],
            check=True, env=env,
            stdin=subprocess.DEVNULL,
        )
    else:
        log.info("Alle gewuenschten Pakete bereits installiert — kein Install.")

    # Remove-Phase (nur mit User-Confirmation)
    if to_remove:
        confirm = False
        if interactive:
            confirm = whiptail.yesno(
                t("remove_title", lang),
                (
                    f"{t('remove_prompt_pre', lang)}\n\n"
                    f"{' '.join(to_remove)}\n\n"
                    f"{t('remove_prompt_post', lang)}"
                ),
                height=15, width=65,
            )
        elif remove_deselected:
            confirm = True

        if confirm:
            log.info("Pakete deinstallieren: %s", " ".join(to_remove))
            subprocess.run(
                ["apt-get", "remove", "-y", "-qq", *to_remove],
                check=True, env=env,
                stdin=subprocess.DEVNULL,
            )
        else:
            log.info("Deinstallation uebersprungen — abgewaehlte Pakete bleiben.")


def _count_upgradable(env: dict[str, str]) -> int:
    """Zaehlt verfuegbare Pakete-Updates via `apt list --upgradable`.

    Header-Zeile ('Listing...') wird uebersprungen, dann Pakete-Zeilen
    mit '/' als Marker (Bash-Pattern: tail -n +2 | grep -c '/').
    """
    result = subprocess.run(
        ["apt", "list", "--upgradable"],
        check=False, env=env,
        text=True, capture_output=True,
    )
    if result.returncode != 0:
        return 0
    lines = result.stdout.splitlines()[1:]  # skip Header
    return sum(1 for line in lines if "/" in line)


def apply_dist_upgrade(
    interactive: bool = False,
    dist_upgrade: bool = False,
    lang: str = "DE",
    logger: logging.Logger | None = None,
) -> None:
    """apt list --upgradable + Confirm-Yesno + dist-upgrade + autoremove + autoclean.

    Nur ausgefuehrt wenn:
      interactive=True  -> User klickt Yes im Whiptail
      interactive=False -> dist_upgrade=True (ENV-Flag)
    """
    log = logger or logging.getLogger(__name__)
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}

    upgradable = _count_upgradable(env)
    if upgradable == 0:
        log.info("Keine Pakete-Updates verfuegbar — System ist aktuell.")
        return

    log.info("%d Pakete-Updates verfuegbar.", upgradable)

    confirm = False
    if interactive:
        confirm = whiptail.yesno(
            t("upgrade_title", lang),
            (
                f"{upgradable} {t('upgrade_prompt_pre', lang)}\n\n"
                f"{t('upgrade_prompt_post', lang)}"
            ),
            height=14, width=65,
        )
    elif dist_upgrade:
        confirm = True

    if not confirm:
        log.info("Updates uebersprungen — System bleibt auf aktuellem Stand.")
        return

    log.info("apt dist-upgrade ausfuehren...")
    # APT::Get::Always-Include-Phased-Updates=true: Ubuntu 24.04+ rollt
    # Updates wellenweise aus (Phased-Update-Percentage). Default-Verhalten
    # von apt-get dist-upgrade -y skippt phased Pakete still ohne Diagnose-
    # Output -> User klickt Yes, sieht aber keine Aktion. Bug-Diagnose
    # 2026-05-07 auf 5521-pmDESK: 9 phased Pakete (gnome-shell-stack +
    # heif-stack) deferred, mit Flag installiert. Latent seit firstboot.sh
    # v0.8.4 (Z831 hatte identischen Pattern ohne Flag).
    subprocess.run(
        ["apt-get",
         "-o", "APT::Get::Always-Include-Phased-Updates=true",
         "dist-upgrade", "-y", "-qq"],
        check=True, env=env, stdin=subprocess.DEVNULL,
    )
    log.info("apt autoremove...")
    subprocess.run(
        ["apt-get", "autoremove", "-y", "-qq"],
        check=True, env=env, stdin=subprocess.DEVNULL,
    )
    log.info("apt autoclean...")
    subprocess.run(
        ["apt-get", "autoclean", "-qq"],
        check=True, env=env, stdin=subprocess.DEVNULL,
    )
    log.info("System aufgeraeumt.")
