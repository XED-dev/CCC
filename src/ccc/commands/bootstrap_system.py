"""bootstrap_system — ccc Verb fuer firstboot.sh Phasen 2-7.

Migriert aus firstboot.sh v0.8.4 main() + collect_inputs_interactive +
apply_*-Phasen-Composition.

Eingabe-Strategie (drei Pfade):
  1. Typer-Args explizit gesetzt -> direkt verwenden
  2. ENV-Vars (XED_LANG, TZ, LOCALES, ...) -> Typer envvar=-Mechanik
  3. TTY + Args/ENV unvollstaendig -> Whiptail-State-Machine (6 Phasen, Back-Button)
  4. Non-TTY + Args/ENV unvollstaendig -> Skript-Defaults

Phasen-Composition (sequentiell):
  1. init_audit_log -> Run-Boundary
  2. self_heal_dpkg -> snap-purge + dpkg-cfg + apt-fix + autoremove
  3. disable_pro_notice -> Pro-Werbung non-destruktiv
  4. apply_timezone(tz)
  5. apply_locales(locales, default_locale)
  6. apply_packages(pkgs, interactive, remove_deselected, lang)
  7. apply_dist_upgrade(interactive, dist_upgrade, lang)
  8. apply_editor()
  9. set_first_run_done() -> Marker

Default-Pre-Select-Tabellen (LOCALE_DEFAULT, PKG_DEFAULT) + I18N-Key-
Mappings (LOCALE_I18N_KEY, PKG_I18N_KEY) sind Bash-1:1-Spiegelungen
firstboot.sh Z542-549 + Z593-604 (Senior-Schaerfung 2026-05-06: explizite
Tabellen statt Heuristik fuer Forensik-Robustheit + User-Behavior-Treue).
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console

from ccc.commands.phases.apt import (
    PKG_MENU_LIST,
    apply_dist_upgrade,
    apply_packages,
)
from ccc.commands.phases.editor import apply_editor
from ccc.commands.phases.locale import (
    LOCALE_MENU_LIST,
    apply_locales,
    apply_timezone,
)
from ccc.system import whiptail
from ccc.system.audit_log import DEFAULT_PATH as AUDIT_LOG_PATH
from ccc.system.audit_log import init_audit_log, phase
from ccc.system.i18n import t
from ccc.system.marker import set_first_run_done
from ccc.system.pkg import current_default_locale, locale_state, pkg_state
from ccc.system.self_heal import disable_pro_notice, self_heal_dpkg

console = Console()

# Default-Werte (Bash-Original collect_inputs_noninteractive Z648-651)
DEFAULT_LANG = "DE"
DEFAULT_TZ = "UTC"
DEFAULT_LOCALES = "de_AT.UTF-8 en_US.UTF-8"
DEFAULT_DEFAULT_LOCALE = "de_AT.UTF-8"
DEFAULT_PKGS = "htop curl wget sudo psmisc net-tools iproute2 iputils-ping gnupg nano"

# TZ-Optionen fuer Whiptail-Menue (Bash collect Phase 2)
TZ_MENU_OPTIONS: tuple[tuple[str, str], ...] = (
    ("UTC", "tz_utc"),
    ("Europe/Vienna", "tz_vienna"),
    ("Asia/Nicosia", "tz_nicosia"),
    ("Europe/Berlin", "tz_berlin"),
    ("Europe/London", "tz_london"),
)

# Default-Pre-Select fuer Locales (Bash-1:1 firstboot.sh Z542-549)
LOCALE_DEFAULT: dict[str, str] = {
    "de_AT.UTF-8": "ON",
    "de_DE.UTF-8": "ON",
    "de_CH.UTF-8": "ON",
    "en_US.UTF-8": "ON",
    "en_GB.UTF-8": "ON",
    "fr_FR.UTF-8": "OFF",
    "it_IT.UTF-8": "OFF",
    "es_ES.UTF-8": "OFF",
}

# I18n-Key-Mapping fuer Locales (explizit, Bash-Abkuerzungs-treu)
LOCALE_I18N_KEY: dict[str, str] = {
    "de_AT.UTF-8": "loc_at",
    "de_DE.UTF-8": "loc_de",
    "de_CH.UTF-8": "loc_ch",
    "en_US.UTF-8": "loc_us",
    "en_GB.UTF-8": "loc_gb",
    "fr_FR.UTF-8": "loc_fr",
    "it_IT.UTF-8": "loc_it",
    "es_ES.UTF-8": "loc_es",
}

# Default-Pre-Select fuer Pakete (Bash-1:1 firstboot.sh Z593-604)
PKG_DEFAULT: dict[str, str] = {
    "htop": "ON", "curl": "ON", "wget": "ON", "sudo": "ON",
    "psmisc": "ON", "net-tools": "ON", "iproute2": "ON",
    "iputils-ping": "ON", "gnupg": "ON", "nano": "ON",
    "pwgen": "OFF", "socat": "OFF",
}

# I18n-Key-Mapping fuer Pakete (explizit, Bash-Abkuerzungs-treu —
# z.B. iputils-ping -> pkg_iping, NICHT Heuristik)
PKG_I18N_KEY: dict[str, str] = {
    "htop": "pkg_htop", "curl": "pkg_curl", "wget": "pkg_wget",
    "sudo": "pkg_sudo", "psmisc": "pkg_psmisc",
    "net-tools": "pkg_nettools", "iproute2": "pkg_iproute2",
    "iputils-ping": "pkg_iping", "gnupg": "pkg_gnupg",
    "nano": "pkg_nano", "pwgen": "pkg_pwgen", "socat": "pkg_socat",
}


def bootstrap_system(
    lang: Optional[str] = typer.Option(None, envvar="XED_LANG"),
    tz: Optional[str] = typer.Option(None, envvar="TZ"),
    locales: Optional[str] = typer.Option(None, envvar="LOCALES"),
    default_locale: Optional[str] = typer.Option(None, envvar="DEFAULT_LOCALE"),
    pkgs: Optional[str] = typer.Option(None, envvar="PKGS"),
    remove_deselected: bool = typer.Option(False, envvar="REMOVE_DESELECTED"),
    dist_upgrade: bool = typer.Option(False, envvar="DIST_UPGRADE"),
) -> None:
    """firstboot Phasen 2-7 als Python-Verb."""

    log = init_audit_log(namespace="xed.bootstrap")

    # Outer-Boundary: 'ccc:bootstrap-system' wraps die gesamte Verb-
    # Ausfuehrung. Bei Exception schreibt der Context-Manager phase_end
    # (rc=1) ins Audit-Log und re-raised. Sprach-Uebergang aus dem
    # firstboot.sh-Phase-4-Hand-off (kein matching phase_end dort) endet
    # in dieses ccc:bootstrap-system start (klare Boundary).
    with phase("ccc:bootstrap-system", logger=log):
        interactive = sys.stdin.isatty()
        args_complete = all([lang, tz, locales, default_locale, pkgs])

        if interactive and not args_complete:
            inputs = _collect_inputs_interactive(
                lang=lang, tz=tz, locales=locales,
                default_locale=default_locale, pkgs=pkgs,
            )
            if inputs is None:
                log.info("User-Abbruch in Whiptail-State-Machine")
                raise typer.Exit(code=1)
            lang = inputs["lang"]
            tz = inputs["tz"]
            locales_list = inputs["locales"]
            default_locale = inputs["default_locale"]
            pkgs_list = inputs["pkgs"]
        else:
            lang = lang or DEFAULT_LANG
            tz = tz or DEFAULT_TZ
            locales_list = (locales or DEFAULT_LOCALES).split()
            default_locale = default_locale or DEFAULT_DEFAULT_LOCALE
            pkgs_list = (pkgs or DEFAULT_PKGS).split()

        console.print(f"[cyan]→ Sprache:[/cyan]        {lang}")
        console.print(f"[cyan]→ Zeitzone:[/cyan]       {tz}")
        console.print(f"[cyan]→ Locales:[/cyan]        {' '.join(locales_list)}")
        console.print(f"[cyan]→ Default-Locale:[/cyan] {default_locale}")
        console.print(f"[cyan]→ Pakete:[/cyan]         {' '.join(pkgs_list)}")
        console.print()

        # Self-Heal-Pre-Phase
        console.print("[cyan]→ Self-Heal: dpkg/apt-State[/cyan]")
        with phase("ccc:self-heal-dpkg", logger=log):
            self_heal_dpkg(logger=log)
        console.print("[cyan]→ Self-Heal: Ubuntu-Pro-Werbung deaktivieren[/cyan]")
        with phase("ccc:self-heal-pro-notice", logger=log):
            disable_pro_notice(logger=log)

        # Phasen-Composition
        console.print("[cyan]→ Phase: Zeitzone[/cyan]")
        with phase("ccc:apply-timezone", logger=log, tz=tz):
            apply_timezone(tz, logger=log)
        console.print("[cyan]→ Phase: Locales[/cyan]")
        with phase(
            "ccc:apply-locales", logger=log, count=len(locales_list),
        ):
            apply_locales(locales_list, default_locale, logger=log)
        console.print("[cyan]→ Phase: Pakete[/cyan]")
        with phase(
            "ccc:apply-packages", logger=log, count=len(pkgs_list),
        ):
            apply_packages(
                pkgs_list, interactive=interactive,
                remove_deselected=remove_deselected, lang=lang, logger=log,
            )
        console.print("[cyan]→ Phase: Dist-Upgrade[/cyan]")
        with phase("ccc:apply-dist-upgrade", logger=log):
            apply_dist_upgrade(
                interactive=interactive, dist_upgrade=dist_upgrade,
                lang=lang, logger=log,
            )
        console.print("[cyan]→ Phase: Editor[/cyan]")
        with phase("ccc:apply-editor", logger=log):
            apply_editor(logger=log)

        set_first_run_done()
        console.print("[green]✔ bootstrap-system durchgelaufen — Box bereit.[/green]")

        # Hint-Block: Audit-Log-Pfad + Lese-Beispiele + Verb-Uebersicht.
        # Wartungs-Pfad sichtbar machen — Logs sind A+O des Developer-Lebens
        # (AI036-Direktive 2026-05-04, Bash-Pattern aus firstboot.sh v0.8.4
        # bei v0.9.0-Refactor zunaechst weggefallen, in v0.1.1 nachgezogen).
        audit_log_str = str(AUDIT_LOG_PATH)
        console.print()
        console.print(f"[cyan]→ Audit-Log dieses Runs:[/cyan] {audit_log_str}")
        console.print(f"    tail -50 {audit_log_str}     # letzte 50 Zeilen")
        console.print(f"    less {audit_log_str}         # vollstaendig durchblaettern")
        console.print(f"    grep ERROR {audit_log_str}   # nur Fehler-Zeilen")
        console.print(f"    grep WARN {audit_log_str}    # nur Warnungen")
        console.print()
        console.print("[cyan]Verfuegbare Verben:[/cyan]")
        console.print("    ccc list                # Rollen")
        console.print("    cca list                # Apps")
        console.print("    cca install <app>       # z.B. cca install gnome")
        console.print()


def _collect_inputs_interactive(
    lang: Optional[str] = None,
    tz: Optional[str] = None,
    locales: Optional[str] = None,
    default_locale: Optional[str] = None,
    pkgs: Optional[str] = None,
) -> Optional[dict]:
    """Whiptail-State-Machine mit Back-Button (6 Phasen).

    Returns dict mit Eingaben oder None bei Abbruch.

    Phasen:
      1 = Sprache (Cancel = Abort-Yesno-Confirm)
      2 = Zeitzone-Menu
      3 = Locales-Checklist
      4 = Default-Locale-Menu (dynamisch aus Phase 3 Locales)
      5 = Pakete-Checklist
      6 = Confirm-Yesno (Yes = break, No = back zu Phase 5)
    """
    state: dict = {
        "lang": lang or DEFAULT_LANG,
        "tz": tz, "locales": None, "default_locale": default_locale,
        "pkgs": None,
    }
    phase = 1

    while phase <= 6:
        if phase == 1:
            rc, val = whiptail.menu(
                "Sprache / Language", "Sprache wählen / Choose language",
                items=[("DE", "Deutsch"), ("EN", "English")],
                height=12, width=60, list_height=2,
            )
            if rc == 0:
                state["lang"] = val
                phase = 2
            else:
                if whiptail.yesno(
                    t("abort_title", state["lang"]),
                    t("abort_prompt", state["lang"]),
                    height=8, width=60,
                ):
                    return None

        elif phase == 2:
            tz_items = [(tz_id, t(key, state["lang"])) for tz_id, key in TZ_MENU_OPTIONS]
            rc, val = whiptail.menu(
                t("tz_title", state["lang"]),
                t("tz_prompt", state["lang"]),
                items=tz_items, height=16, width=70, list_height=5,
            )
            if rc == 0:
                state["tz"] = val
                phase = 3
            else:
                phase = 1

        elif phase == 3:
            loc_items = [
                (loc, t(LOCALE_I18N_KEY[loc], state["lang"]),
                 locale_state(loc, default=LOCALE_DEFAULT[loc]))
                for loc in LOCALE_MENU_LIST
            ]
            rc, val = whiptail.checklist(
                t("loc_title", state["lang"]),
                t("loc_prompt", state["lang"]),
                items=loc_items, height=18, width=65, list_height=8,
            )
            if rc == 0:
                if not val:
                    whiptail.msgbox(
                        t("loc_none_title", state["lang"]),
                        t("loc_none", state["lang"]),
                        height=8, width=60,
                    )
                    continue  # Re-Prompt Phase 3 (kein decrement)
                state["locales"] = val
                phase = 4
            else:
                phase = 2

        elif phase == 4:
            menu_items = [(loc, "") for loc in state["locales"]]
            rc, val = whiptail.menu(
                t("defloc_title", state["lang"]),
                t("defloc_prompt", state["lang"]),
                items=menu_items,
                height=max(12, len(state["locales"]) + 8),
                width=60,
                list_height=len(state["locales"]),
            )
            if rc == 0:
                state["default_locale"] = val
                phase = 5
            else:
                phase = 3

        elif phase == 5:
            pkg_items = [
                (pkg, t(PKG_I18N_KEY[pkg], state["lang"]),
                 pkg_state(pkg, default=PKG_DEFAULT[pkg]))
                for pkg in PKG_MENU_LIST
            ]
            rc, val = whiptail.checklist(
                t("pkgs_title", state["lang"]),
                t("pkgs_prompt", state["lang"]),
                items=pkg_items, height=20, width=70, list_height=12,
            )
            if rc == 0:
                state["pkgs"] = val
                phase = 6
            else:
                phase = 4

        elif phase == 6:
            confirm_text = (
                f"{t('confirm_tz', state['lang'])}{state['tz']}\n"
                f"{t('confirm_locales', state['lang'])}{' '.join(state['locales'])}\n"
                f"{t('confirm_defloc', state['lang'])}{state['default_locale']}\n"
                f"{t('confirm_pkgs', state['lang'])}{' '.join(state['pkgs'])}\n\n"
                f"{t('confirm_prompt', state['lang'])}"
            )
            if whiptail.yesno(
                t("confirm_title", state["lang"]),
                confirm_text, height=18, width=70,
            ):
                break
            else:
                phase = 5

    return state
