"""locale — apply_timezone + apply_locales Phase-Funktionen.

Migriert aus firstboot.sh v0.8.4 apply_timezone (Z662-672) +
apply_locales (Z676-729). LOCALE_MENU_LIST + Diff-Logik enable/disable
gespiegelt 1:1.

apply_timezone: ln -sfn /usr/share/zoneinfo/<tz> /etc/localtime +
                /etc/timezone-Update + dpkg-reconfigure tzdata.
                no-deletion-konform via ln -sfn (atomic replace internal).

apply_locales: Diff-Logik to_enable/to_disable, sed-aequivalent via
               re.sub(re.MULTILINE), locale-gen + update-locale.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Sequence

from ccc.system.pkg import LOCALE_GEN_PATH, locale_status_in_content

ZONEINFO_DIR = Path("/usr/share/zoneinfo")
TIMEZONE_FILE = Path("/etc/timezone")

# Locales die im Whiptail-Menue angeboten werden (Bash LOCALE_MENU_LIST).
# Bei deselect=disable-Diff: nur Menue-Locales kommen fuer Disable in Frage —
# User-eigene Custom-Locales in /etc/locale.gen bleiben unangetastet.
LOCALE_MENU_LIST: tuple[str, ...] = (
    "de_AT.UTF-8", "de_DE.UTF-8", "de_CH.UTF-8",
    "en_US.UTF-8", "en_GB.UTF-8",
    "fr_FR.UTF-8", "it_IT.UTF-8", "es_ES.UTF-8",
)


def apply_timezone(
    tz: str,
    zoneinfo_dir: Path | None = None,
    timezone_file: Path | None = None,
    logger: logging.Logger | None = None,
) -> None:
    """Setzt System-TZ via ln -sfn /etc/localtime + /etc/timezone-Update +
    dpkg-reconfigure tzdata. RuntimeError wenn zoneinfo-Datei fehlt.

    zoneinfo_dir + timezone_file als Optional-Args fuer Testbarkeit
    (Pattern-Symmetrie zu apply_locales(locale_gen=...) und
    pro_notice.disable_pro_notice(esm_hook=...)).
    """
    log = logger or logging.getLogger(__name__)
    zi_dir = zoneinfo_dir or ZONEINFO_DIR
    tz_file = timezone_file or TIMEZONE_FILE

    zoneinfo = zi_dir / tz
    if not zoneinfo.exists():
        raise RuntimeError(
            f"Unbekannte Zeitzone: {tz} ({zoneinfo} existiert nicht)"
        )
    log.info("Zeitzone setzen: %s", tz)

    # ln -sfn: atomic-overwrite via ln-internals (no-deletion-konform —
    # ersetzt vorhandenen Symlink ohne expliziten unlink-Call)
    subprocess.run(
        ["ln", "-sfn", str(zoneinfo), "/etc/localtime"],
        check=True,
    )
    tz_file.write_text(f"{tz}\n", encoding="utf-8")

    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    subprocess.run(
        ["dpkg-reconfigure", "-f", "noninteractive", "tzdata"],
        check=True, env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    log.info("Zeitzone gesetzt: %s", tz)


def apply_locales(
    locales: Sequence[str],
    default_locale: str,
    logger: logging.Logger | None = None,
    locale_gen: Path | None = None,
    menu_list: Sequence[str] = LOCALE_MENU_LIST,
) -> None:
    """Diff-Logik enable/disable + sed-aequivalent + locale-gen + update-locale.

    Diff-Strategie:
      to_enable  = in `locales`, aber nicht aktiv in /etc/locale.gen
      to_disable = in menu_list + aktiv, aber nicht in `locales`
                   (User-eigene Custom-Locales bleiben unangetastet — nur
                   Menue-Locales kommen fuer Disable in Frage)
    """
    log = logger or logging.getLogger(__name__)
    path = locale_gen or LOCALE_GEN_PATH

    initial_content = path.read_text(encoding="utf-8") if path.is_file() else ""

    # Status pro Locale einmal berechnen (Performance + Determinismus)
    relevant = set(locales) | set(menu_list)
    status_map = {loc: locale_status_in_content(initial_content, loc) for loc in relevant}

    to_enable = [loc for loc in locales if status_map[loc] != "ACTIVE"]
    to_disable = [
        loc for loc in menu_list
        if status_map[loc] == "ACTIVE" and loc not in locales
    ]

    new_content = initial_content

    if to_enable:
        log.info("Locales aktivieren: %s", " ".join(to_enable))
        for loc in to_enable:
            pattern = re.escape(loc)
            if status_map[loc] == "DISABLED":
                # uncomment via regex-replace
                new_content = re.sub(
                    rf"^# *({pattern}[ \t]+UTF-8)",
                    r"\1",
                    new_content,
                    flags=re.MULTILINE,
                )
            else:  # ABSENT — append
                if new_content and not new_content.endswith("\n"):
                    new_content += "\n"
                new_content += f"{loc} UTF-8\n"
    else:
        log.info("Alle gewuenschten Locales bereits aktiv — kein Enable.")

    if to_disable:
        log.info("Locales deaktivieren: %s", " ".join(to_disable))
        for loc in to_disable:
            pattern = re.escape(loc)
            new_content = re.sub(
                rf"^({pattern}[ \t]+UTF-8)",
                r"# \1",
                new_content,
                flags=re.MULTILINE,
            )

    if new_content != initial_content:
        path.write_text(new_content, encoding="utf-8")

    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    subprocess.run(
        ["locale-gen"],
        check=True, env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["update-locale", f"LANG={default_locale}", f"LC_CTYPE={default_locale}"],
        check=True, env=env,
    )
    log.info("Default-Locale gesetzt: %s (in /etc/default/locale)", default_locale)
