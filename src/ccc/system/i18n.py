"""i18n — DE/EN-Strings fuer ccc bootstrap-system Phasen + Whiptail-TUI.

Migriert aus firstboot.sh v0.8.4 init_strings() (~167 Zeilen Bash, hier
strukturierter Dict-Lookup). Phase 1 (Eingaben sammeln) entfaellt in
v0.9.0 durch ENV+Args-Pattern — deren Strings sind obsolet. Phase 7
(Python-Tool-Install Yesno) bleibt in firstboot.sh-Bash-Welt.

Bottom-up-Sortierung: erst Phase-Funktions-Strings (SS3.4 Console-Output),
dann Whiptail-TUI-Strings (SS3.3 Wrapper-Texte).
"""

from __future__ import annotations

DEFAULT_LANG = "DE"

STRINGS: dict[str, dict[str, str]] = {
    "DE": {
        # --- Buttons + Abbrechen-Dialog ---
        "back": "Zurück",
        "apply": "Anwenden",
        "abort_title": "Abbrechen?",
        "abort_prompt": "Skript wirklich abbrechen?",

        # --- Phase 2: Zeitzone ---
        "tz_title": "Server-Zeitzone",
        "tz_prompt": "Empfehlung: UTC für Server. Lokale Zeit besser pro User-Shell setzen.",
        "tz_utc": "Empfohlen — keine DST-Sprünge, saubere Logs",
        "tz_vienna": "DACH-Standard (CET/CEST)",
        "tz_nicosia": "Cyprus / EET (DevOps-Standort)",
        "tz_berlin": "Generisch DACH",
        "tz_london": "UK / GMT",

        # --- Phase 3: Locales ---
        "loc_title": "Locales generieren",
        "loc_prompt": "Welche Locales sollen verfügbar sein? (Leertaste = toggle)",
        "loc_at": "Österreich",
        "loc_de": "Deutschland",
        "loc_ch": "Schweiz",
        "loc_us": "US-Englisch",
        "loc_gb": "UK-Englisch",
        "loc_fr": "Frankreich",
        "loc_it": "Italien",
        "loc_es": "Spanien",
        "loc_none_title": "Keine Locales",
        "loc_none": "Keine Locales ausgewählt. Bitte mindestens eine wählen.",

        # --- Phase 4: Default-Locale ---
        "defloc_title": "Default-Locale",
        "defloc_prompt": "Welche dieser Locales als System-Default (LANG)?",

        # --- Phase 5: Pakete ---
        "pkgs_title": "Basis-Pakete",
        "pkgs_prompt": "Welche Tools installieren? (Leertaste = toggle, abwählen = deinstallieren mit Rückfrage)",
        "pkg_htop": "Prozess-Monitor",
        "pkg_curl": "HTTP-Client",
        "pkg_wget": "HTTP-Downloader",
        "pkg_sudo": "Privilege-Wechsel",
        "pkg_psmisc": "killall, fuser, pstree",
        "pkg_nettools": "ifconfig, route, netstat",
        "pkg_iproute2": "ip a, ip r, ss",
        "pkg_iping": "ping",
        "pkg_gnupg": "GPG für Repos",
        "pkg_nano": "Editor",
        "pkg_pwgen": "Passwort-Generator",
        "pkg_socat": "Universal-Socket-Tool",

        # --- Phase 5b: Dist-Upgrade ---
        "upgrade_title": "System-Updates",
        "upgrade_prompt_pre": "Pakete-Updates verfügbar.",
        "upgrade_prompt_post": "Jetzt 'apt dist-upgrade + autoremove + autoclean' durchführen?\n\n(Empfohlen für aktuelle Box. Kann je nach Update-Umfang\neinige Minuten dauern.)",

        # --- Phase 6: Confirm ---
        "confirm_title": "Übersicht — bitte prüfen",
        "confirm_tz": "Zeitzone:       ",
        "confirm_locales": "Locales:        ",
        "confirm_defloc": "Default-Locale: ",
        "confirm_pkgs": "Pakete:         ",
        "confirm_prompt": "Anwenden?",

        # --- Remove-Confirmation (apply_packages) ---
        "remove_title": "Pakete deinstallieren?",
        "remove_prompt_pre": "Folgende Pakete sind installiert, aber im Menü abgewählt:",
        "remove_prompt_post": "Mit 'apt remove' deinstallieren?\n\n(Konfigurations-Dateien bleiben erhalten — kein 'purge'.)",

        # --- Finish ---
        "finish_title": "Fertig",
        "finish_header": "Setup abgeschlossen.",
        "finish_tz": "Zeitzone:       ",
        "finish_defloc": "Default-Locale: ",
        "finish_hint": "Bitte einmal 'exit' und neu einloggen,\ndamit die Locale in der Shell-Session greift.",
    },
    "EN": {
        # --- Buttons + Abort dialog ---
        "back": "Back",
        "apply": "Apply",
        "abort_title": "Abort?",
        "abort_prompt": "Really abort the script?",

        # --- Phase 2: Timezone ---
        "tz_title": "Server Timezone",
        "tz_prompt": "Recommendation: UTC for servers. Set local time per user shell.",
        "tz_utc": "Recommended — no DST jumps, clean logs",
        "tz_vienna": "DACH standard (CET/CEST)",
        "tz_nicosia": "Cyprus / EET (DevOps location)",
        "tz_berlin": "Generic DACH",
        "tz_london": "UK / GMT",

        # --- Phase 3: Locales ---
        "loc_title": "Generate Locales",
        "loc_prompt": "Which locales should be available? (Space = toggle)",
        "loc_at": "Austria",
        "loc_de": "Germany",
        "loc_ch": "Switzerland",
        "loc_us": "US English",
        "loc_gb": "UK English",
        "loc_fr": "France",
        "loc_it": "Italy",
        "loc_es": "Spain",
        "loc_none_title": "No locales",
        "loc_none": "No locales selected. Please select at least one.",

        # --- Phase 4: Default Locale ---
        "defloc_title": "Default Locale",
        "defloc_prompt": "Which of these locales as system default (LANG)?",

        # --- Phase 5: Packages ---
        "pkgs_title": "Base Packages",
        "pkgs_prompt": "Which tools to install? (Space = toggle, deselect = remove with confirmation)",
        "pkg_htop": "Process monitor",
        "pkg_curl": "HTTP client",
        "pkg_wget": "HTTP downloader",
        "pkg_sudo": "Privilege switch",
        "pkg_psmisc": "killall, fuser, pstree",
        "pkg_nettools": "ifconfig, route, netstat",
        "pkg_iproute2": "ip a, ip r, ss",
        "pkg_iping": "ping",
        "pkg_gnupg": "GPG for repos",
        "pkg_nano": "Editor",
        "pkg_pwgen": "Password generator",
        "pkg_socat": "Universal socket tool",

        # --- Phase 5b: Dist-Upgrade ---
        "upgrade_title": "System Updates",
        "upgrade_prompt_pre": "package updates available.",
        "upgrade_prompt_post": "Run 'apt dist-upgrade + autoremove + autoclean' now?\n\n(Recommended for an up-to-date box. May take some\nminutes depending on update size.)",

        # --- Phase 6: Confirm ---
        "confirm_title": "Summary — please review",
        "confirm_tz": "Timezone:       ",
        "confirm_locales": "Locales:        ",
        "confirm_defloc": "Default-Locale: ",
        "confirm_pkgs": "Packages:       ",
        "confirm_prompt": "Apply?",

        # --- Remove Confirmation ---
        "remove_title": "Remove packages?",
        "remove_prompt_pre": "The following packages are installed but deselected in the menu:",
        "remove_prompt_post": "Remove with 'apt remove'?\n\n(Configuration files are kept — no 'purge'.)",

        # --- Finish ---
        "finish_title": "Done",
        "finish_header": "Setup complete.",
        "finish_tz": "Timezone:       ",
        "finish_defloc": "Default-Locale: ",
        "finish_hint": "Please 'exit' and re-login\nso the locale takes effect in the shell session.",
    },
}


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Lookup String fuer key in lang. Drei-stufiger Fallback:
    lang-spezifisch -> DEFAULT_LANG -> '<missing:key>'-marker.

    Erlaubt graceful degradation wenn Key fehlt (kein KeyError-Crash
    in der TUI).
    """
    return STRINGS.get(lang, STRINGS[DEFAULT_LANG]).get(
        key, STRINGS[DEFAULT_LANG].get(key, f"<missing:{key}>")
    )
