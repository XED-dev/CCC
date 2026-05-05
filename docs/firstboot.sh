#!/bin/bash
# firstboot.sh — cBOX@ /Container Control Bash-Basis-Setup für frische Debian/Ubuntu-Boxen
#
# Quelle:    https://github.com/XED-dev/CCC
#
# Aufruf auf frischen Debian/Ubuntu-LXC-Boxen (Pre-Step nötig — minimal-Templates
# haben kein curl vorinstalliert):
#
#   apt update && apt install -y curl ca-certificates
#   bash <(curl -s https://ccc.xed.dev/firstboot.sh)
#
# Oder als One-Liner:
#   apt-get update -qq && apt-get install -y -qq --no-install-recommends \
#     curl ca-certificates && bash <(curl -s https://ccc.xed.dev/firstboot.sh)
#
# Lokal:     bash firstboot.sh
#
# Non-Tty:   TZ=UTC LOCALES="de_AT.UTF-8 en_US.UTF-8" \
#              DEFAULT_LOCALE=de_AT.UTF-8 \
#              bash <(curl -s https://ccc.xed.dev/firstboot.sh)
#
# Was es tut:
#   Phase 0 — Pre-Flight (root-Check, Distro-Check, apt-Bootstrap, TTY-Detect)
#   Phase 1 — Eingaben sammeln (Whiptail-TUI bei TTY, ENV-Vars sonst)
#   Phase 2 — Zeitzone setzen
#   Phase 3 — Locales generieren + Default-Locale
#   Phase 4 — Basis-Pakete installieren
#   Phase 5 — EDITOR=nano in /etc/environment (idempotent)
#   Phase 6 — Abschluss-Banner
#
# Idempotenz: kann beliebig oft aufgerufen werden, konvergiert zum Soll-Zustand.
#
# TTY-Hinweis: `bash <(curl -s URL)` (Process Substitution) bewahrt TTY und
# erlaubt Whiptail. `curl URL | bash` (klassische Pipe) verbraucht stdin und
# erzwingt non-interactive Mode mit ENV-Defaults.
#
# Lizenz: MIT (siehe LICENSE im XED-dev/CCC-Repo)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Hinweis: Kein LC_ALL=C — würde Whiptail in C/POSIX-Charset zwingen und
# Umlaute (Österreich, Französisch, …) zerschießen. Die Locale-Warning beim
# allerersten Lauf ist kosmetisch und verschwindet nach Phase 3.

# === Globals ===

VERSION="0.8.4"
SCRIPT_NAME="firstboot.sh"
TTY_MODE=""
LANG_CHOICE=""   # "DE" oder "EN", gesetzt durch state-machine Phase 1

# Marker-Datei: existiert nach erstem erfolgreichen Run.
# Trennt allerersten-Run-Verhalten (Skript-Defaults greifen) von Re-Run
# (nur System-Ist-Zustand zählt — User-Wille respektieren).
FIRSTBOOT_MARKER="/var/lib/xed-ccc/firstboot.applied"

# ccc + cca CC-Suite-Installations-Pfade (Phase 7)
CCC_INSTALL_DIR="/opt/xed-ccc"
CCC_VENV_DIR="${CCC_INSTALL_DIR}/.venv"
CCC_BIN_LINK="/usr/local/bin/ccc"
CCC_REPO_URL="https://github.com/XED-dev/CCC.git"

CCA_INSTALL_DIR="/opt/xed-cca"
CCA_VENV_DIR="${CCA_INSTALL_DIR}/.venv"
CCA_BIN_LINK="/usr/local/bin/cca"
CCA_REPO_URL="https://github.com/XED-dev/CCA.git"

# pipx-System-Setup (Phase 7+7b ab v0.8.0 — pipx-basierte CLI-Tool-Distribution)
# Statt git-clone + manueller venv: pipx zieht xed-ccc + xed-cca von PyPI in
# isolierte venvs unter $PIPX_HOME, mit Symlinks in $PIPX_BIN_DIR.
# Update-Pfad: pipx upgrade xed-ccc xed-cca.
# Self-Heal-Pfad: pipx reinstall xed-ccc.
# Pattern: reference_pipx_for_cli_tools.md (AI036, 2026-05-04).
PIPX_HOME_DIR="/opt/pipx"
PIPX_BIN_DIR_PATH="/usr/local/bin"

# Snap-Redirect-Pakete auf Ubuntu 22.04+ — bricht im LXC ohne snapd.
# Wird im self_heal_dpkg() purgiert vor jedem apt-Aufruf in Phase 7.
# Pattern: reference_no_snap_in_lxc.md (AI036, 2026-05-04).
SNAP_REDIRECT_PACKAGES_LIST="firefox thunderbird chromium-browser gnome-software-plugin-snap snapd"

# Persistente Audit-Log-Datei (Forensik-Trail über alle firstboot-Runs).
# Plus: msgbox-Konservation am Ende von Phase 7+7b (current-run UI-Anzeige).
# Beide ergänzen sich — Log = Forensik, msgbox = User-Sichtbarkeit.
FIRSTBOOT_LOG_FILE="/var/log/xed-firstboot.log"

# Cascade-Schutz für apt purge: Hard-Deps werden automatisch mit-entfernt;
# bei system-critical Meta-Paketen zerstört das den Display-Stack. Whitelist
# wird in safe_purge() gegen die simulate-Cascade geprüft, Abort bei Treffer.
CRITICAL_PACKAGES_WHITELIST=(
    "vanilla-gnome-desktop"
    "gnome-core"
    "gnome-shell"
    "gnome-shell-common"
    "gnome-session"
    "gnome-terminal"
    "ubuntu-minimal"
    "xrdp"
    "xorgxrdp"
    "dbus-x11"
)

# Pakete, die im Whiptail-Menü angeboten werden (für deselect=uninstall-Diff).
# Pakete ausserhalb dieser Liste bleiben unangetastet — Sicherheits-Schutzschicht
# gegen versehentliche Deinstallation von System-Paketen.
PKG_MENU_LIST="htop curl wget sudo psmisc net-tools iproute2 iputils-ping gnupg nano pwgen socat"

# Locales, die im Whiptail-Menü angeboten werden (für deselect=disable-Diff).
# Locales ausserhalb dieser Liste bleiben unangetastet — User-eigene Custom-Locales
# in /etc/locale.gen werden nicht angefasst.
LOCALE_MENU_LIST="de_AT.UTF-8 de_DE.UTF-8 de_CH.UTF-8 en_US.UTF-8 en_GB.UTF-8 fr_FR.UTF-8 it_IT.UTF-8 es_ES.UTF-8"

# Konfigurations-Variablen, gefüllt durch Phase 1
TZ_VALUE=""
LOCALES_VALUE=""
DEFAULT_LOCALE_VALUE=""
PKGS_VALUE=""

# === Output-Helpers ===

banner() {
    echo
    echo "========================================================================"
    echo "  cBOX@ /Container Control — ${SCRIPT_NAME} v${VERSION}"
    echo "  Basis-Setup für frische Debian/Ubuntu-LXC-Boxen"
    echo "  cBOX.at/YOU by XED.dev Tools via Collective Context (CC)"
    echo "========================================================================"
    echo
}

# Output-Helper schreiben in drei Ziele:
# 1. stdout/stderr (immer) — User-Sichtbarkeit
# 2. $FIRSTBOOT_LOG_FILE (immer wenn gesetzt) — persistenter Audit-Trail
# 3. $PHASE_LOG_FILE (wenn gesetzt — nur Phase 7+7b) — current-run msgbox

# Append zur persistenten Audit-Log-Datei mit ISO-Zeitstempel.
log_to_file() {
    local level="$1"; shift
    [ -n "${FIRSTBOOT_LOG_FILE:-}" ] || return 0
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$level] $*" >> "$FIRSTBOOT_LOG_FILE" 2>/dev/null || true
}

# Initialisiert die Log-Datei mit Run-Header. Wird in main() nach require_root
# aufgerufen (root nötig für /var/log-Zugriff).
init_log_file() {
    [ -n "${FIRSTBOOT_LOG_FILE:-}" ] || return 0
    mkdir -p "$(dirname "$FIRSTBOOT_LOG_FILE")" 2>/dev/null || true
    {
        echo ""
        echo "================================================================"
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [INIT] firstboot.sh v${VERSION} run start"
        echo "================================================================"
    } >> "$FIRSTBOOT_LOG_FILE" 2>/dev/null || true
}

err()  {
    echo "ERROR: $*" >&2
    log_to_file "ERROR" "$*"
    if [ -n "${PHASE_LOG_FILE:-}" ]; then
        echo "ERROR: $*" >> "$PHASE_LOG_FILE" 2>/dev/null || true
    fi
}
info() {
    echo "→ $*"
    log_to_file "INFO" "$*"
    if [ -n "${PHASE_LOG_FILE:-}" ]; then
        echo "→ $*" >> "$PHASE_LOG_FILE" 2>/dev/null || true
    fi
}
ok()   {
    echo "✔ $*"
    log_to_file "OK" "$*"
    if [ -n "${PHASE_LOG_FILE:-}" ]; then
        echo "✔ $*" >> "$PHASE_LOG_FILE" 2>/dev/null || true
    fi
}
warn() {
    echo "⚠ $*" >&2
    log_to_file "WARN" "$*"
    if [ -n "${PHASE_LOG_FILE:-}" ]; then
        echo "⚠ $*" >> "$PHASE_LOG_FILE" 2>/dev/null || true
    fi
}

# === Idempotenz-Helper ===

# Existiert Marker-Datei? (= bereits ein erfolgreicher Run gelaufen)
is_first_run() {
    [ ! -f "$FIRSTBOOT_MARKER" ]
}

# Ist Locale (z.B. "de_AT.UTF-8") in /etc/locale.gen UNcommented?
locale_is_active() {
    local loc="$1"
    local pattern="${loc//./\\.}"
    grep -qE "^[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null
}

# Drei-wertiger Locale-Status:
#   ACTIVE   — uncommented in /etc/locale.gen (= aktiv)
#   DISABLED — commented in /etc/locale.gen (= User hat abgewählt)
#   ABSENT   — gar nicht in /etc/locale.gen (= unbekannt)
locale_status() {
    local loc="$1"
    local pattern="${loc//./\\.}"
    if grep -qE "^[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null; then
        echo "ACTIVE"
    elif grep -qE "^#[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null; then
        echo "DISABLED"
    else
        echo "ABSENT"
    fi
}

# Ist Paket installiert? (dpkg-query)
pkg_is_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

# Pre-Select-Helper für Whiptail-Checklists.
#
# Locale: drei-wertig. ACTIVE/DISABLED sind explizite User-States, ABSENT
# fällt auf $default zurück (Skript-Default greift).
#
# Pakete: zwei-wertig. INSTALLED → ON. Bei UNINSTALLED entscheidet
# is_first_run: erster Run → Skript-Default, Re-Run → OFF (User-Wille).
locale_state() {
    case "$(locale_status "$1")" in
        ACTIVE)   echo "ON" ;;
        DISABLED) echo "OFF" ;;
        *)        # ABSENT
            if is_first_run; then echo "$2"; else echo "OFF"; fi
            ;;
    esac
}
pkg_state() {
    if pkg_is_installed "$1"; then
        echo "ON"
    elif is_first_run; then
        echo "$2"
    else
        echo "OFF"
    fi
}

# Aktueller System-Default-Locale (für `whiptail --default-item`)
current_default_locale() {
    if [ -r /etc/default/locale ]; then
        grep '^LANG=' /etc/default/locale 2>/dev/null | cut -d= -f2 | tr -d '"'
    fi
}

# === I18n — DE/EN-Strings ===
# Aufgerufen NACH Sprachwahl-Phase (oder mit Default DE wenn non-interactive).
# Alle user-facing Whiptail-Texte werden hier gesetzt; info/ok/err-Logs bleiben DE.

init_strings() {
    case "${LANG_CHOICE:-DE}" in
        EN)
            # --- Buttons ---
            T_BACK="Back"
            T_APPLY="Apply"

            # --- Phase 1: Sprache (für Abort-Dialog) ---
            T_ABORT_TITLE="Abort?"
            T_ABORT_PROMPT="Really abort the script?"

            # --- Phase 2: Zeitzone ---
            T_TZ_TITLE="Server Timezone"
            T_TZ_PROMPT="Recommendation: UTC for servers. Set local time per user shell."
            T_TZ_UTC="Recommended — no DST jumps, clean logs"
            T_TZ_VIENNA="DACH standard (CET/CEST)"
            T_TZ_NICOSIA="Cyprus / EET (DevOps location)"
            T_TZ_BERLIN="Generic DACH"
            T_TZ_LONDON="UK / GMT"

            # --- Phase 3: Locales ---
            T_LOC_TITLE="Generate Locales"
            T_LOC_PROMPT="Which locales should be available? (Space = toggle)"
            T_LOC_AT="Austria"
            T_LOC_DE="Germany"
            T_LOC_CH="Switzerland"
            T_LOC_US="US English"
            T_LOC_GB="UK English"
            T_LOC_FR="France"
            T_LOC_IT="Italy"
            T_LOC_ES="Spain"
            T_LOC_NONE_TITLE="No locales"
            T_LOC_NONE="No locales selected. Please select at least one."

            # --- Phase 4: Default-Locale ---
            T_DEFLOC_TITLE="Default Locale"
            T_DEFLOC_PROMPT="Which of these locales as system default (LANG)?"

            # --- Phase 5: Pakete ---
            T_PKGS_TITLE="Base Packages"
            T_PKGS_PROMPT="Which tools to install? (Space = toggle, deselect = remove with confirmation)"
            T_PKG_HTOP="Process monitor"
            T_PKG_CURL="HTTP client"
            T_PKG_WGET="HTTP downloader"
            T_PKG_SUDO="Privilege switch"
            T_PKG_PSMISC="killall, fuser, pstree"
            T_PKG_NETTOOLS="ifconfig, route, netstat"
            T_PKG_IPROUTE2="ip a, ip r, ss"
            T_PKG_IPING="ping"
            T_PKG_GNUPG="GPG for repos"
            T_PKG_NANO="Editor"
            T_PKG_PWGEN="Password generator"
            T_PKG_SOCAT="Universal socket tool"

            # --- Phase 6: Confirm ---
            T_CONFIRM_TITLE="Summary — please review"
            T_CONFIRM_TZ="Timezone:       "
            T_CONFIRM_LOCALES="Locales:        "
            T_CONFIRM_DEFLOC="Default-Locale: "
            T_CONFIRM_PKGS="Packages:       "
            T_CONFIRM_PROMPT="Apply?"

            # --- Remove-Confirmation (apply_packages) ---
            T_REMOVE_TITLE="Remove packages?"
            T_REMOVE_PROMPT_PRE="The following packages are installed but deselected in the menu:"
            T_REMOVE_PROMPT_POST="Remove with 'apt remove'?\n\n(Configuration files are kept — no 'purge'.)"

            # --- Dist-Upgrade-Prompt ---
            T_UPGRADE_TITLE="System Updates"
            T_UPGRADE_PROMPT_PRE="package updates available."
            T_UPGRADE_PROMPT_POST="Run 'apt dist-upgrade + autoremove + autoclean' now?\n\n(Recommended for an up-to-date box. May take some\nminutes depending on update size.)"

            # --- Phase 7: ccc-Python-Tool-Bridge ---
            T_CCC_TITLE="cBOX@ /CCC Python Tool"
            T_CCC_PROMPT="firstboot.sh is the Bash basic setup. The next step is\nthe cBOX@ /CC-Suite (Python tools) for the actual work:\n\n  ccc create pmDESK        # role composition (Gnome + xrdp + ...)\n  cca install gnome        # atomic app install\n  cca install ghost        # blog / CMS\n  cca install wordops      # LEMP stack manager\n  cca install miab         # mail-in-a-box\n\nInstall Python stack + ccc + cca tools now?\n\n(Optional — can also be done later by re-running\n this firstboot.sh.)"

            # --- Finish ---
            T_FINISH_TITLE="Done"
            T_FINISH_HEADER="Setup complete."
            T_FINISH_TZ="Timezone:       "
            T_FINISH_DEFLOC="Default-Locale: "
            T_FINISH_HINT="Please 'exit' and re-login\\nso the locale takes effect in the shell session."
            ;;
        *)
            # DE default (Fallback wenn LANG_CHOICE leer)
            # --- Buttons ---
            T_BACK="Zurück"
            T_APPLY="Anwenden"

            # --- Phase 1 ---
            T_ABORT_TITLE="Abbrechen?"
            T_ABORT_PROMPT="Skript wirklich abbrechen?"

            # --- Phase 2: Zeitzone ---
            T_TZ_TITLE="Server-Zeitzone"
            T_TZ_PROMPT="Empfehlung: UTC für Server. Lokale Zeit besser pro User-Shell setzen."
            T_TZ_UTC="Empfohlen — keine DST-Sprünge, saubere Logs"
            T_TZ_VIENNA="DACH-Standard (CET/CEST)"
            T_TZ_NICOSIA="Cyprus / EET (DevOps-Standort)"
            T_TZ_BERLIN="Generisch DACH"
            T_TZ_LONDON="UK / GMT"

            # --- Phase 3: Locales ---
            T_LOC_TITLE="Locales generieren"
            T_LOC_PROMPT="Welche Locales sollen verfügbar sein? (Leertaste = toggle)"
            T_LOC_AT="Österreich"
            T_LOC_DE="Deutschland"
            T_LOC_CH="Schweiz"
            T_LOC_US="US-Englisch"
            T_LOC_GB="UK-Englisch"
            T_LOC_FR="Frankreich"
            T_LOC_IT="Italien"
            T_LOC_ES="Spanien"
            T_LOC_NONE_TITLE="Keine Locales"
            T_LOC_NONE="Keine Locales ausgewählt. Bitte mindestens eine wählen."

            # --- Phase 4: Default-Locale ---
            T_DEFLOC_TITLE="Default-Locale"
            T_DEFLOC_PROMPT="Welche dieser Locales als System-Default (LANG)?"

            # --- Phase 5: Pakete ---
            T_PKGS_TITLE="Basis-Pakete"
            T_PKGS_PROMPT="Welche Tools installieren? (Leertaste = toggle, abwählen = deinstallieren mit Rückfrage)"
            T_PKG_HTOP="Prozess-Monitor"
            T_PKG_CURL="HTTP-Client"
            T_PKG_WGET="HTTP-Downloader"
            T_PKG_SUDO="Privilege-Wechsel"
            T_PKG_PSMISC="killall, fuser, pstree"
            T_PKG_NETTOOLS="ifconfig, route, netstat"
            T_PKG_IPROUTE2="ip a, ip r, ss"
            T_PKG_IPING="ping"
            T_PKG_GNUPG="GPG für Repos"
            T_PKG_NANO="Editor"
            T_PKG_PWGEN="Passwort-Generator"
            T_PKG_SOCAT="Universal-Socket-Tool"

            # --- Phase 6: Confirm ---
            T_CONFIRM_TITLE="Übersicht — bitte prüfen"
            T_CONFIRM_TZ="Zeitzone:       "
            T_CONFIRM_LOCALES="Locales:        "
            T_CONFIRM_DEFLOC="Default-Locale: "
            T_CONFIRM_PKGS="Pakete:         "
            T_CONFIRM_PROMPT="Anwenden?"

            # --- Remove-Confirmation ---
            T_REMOVE_TITLE="Pakete deinstallieren?"
            T_REMOVE_PROMPT_PRE="Folgende Pakete sind installiert, aber im Menü abgewählt:"
            T_REMOVE_PROMPT_POST="Mit 'apt remove' deinstallieren?\n\n(Konfigurations-Dateien bleiben erhalten — kein 'purge'.)"

            # --- Dist-Upgrade-Prompt ---
            T_UPGRADE_TITLE="System-Updates"
            T_UPGRADE_PROMPT_PRE="Pakete-Updates verfügbar."
            T_UPGRADE_PROMPT_POST="Jetzt 'apt dist-upgrade + autoremove + autoclean' durchführen?\n\n(Empfohlen für aktuelle Box. Kann je nach Update-Umfang\neinige Minuten dauern.)"

            # --- Phase 7: ccc-Python-Tool-Bridge ---
            T_CCC_TITLE="cBOX@ /CCC Python-Tool"
            T_CCC_PROMPT="firstboot.sh ist das Bash-Basis-Setup. Als nächster\nSchritt steht die cBOX@ /CC-Suite (Python-Tools) bereit:\n\n  ccc create pmDESK        # Rollen-Komposition (Gnome + xrdp + ...)\n  cca install gnome        # atomare App-Installation\n  cca install ghost        # Blog / CMS\n  cca install wordops      # LEMP-Stack-Manager\n  cca install miab         # Mail-in-a-Box\n\nPython-Stack + ccc + cca jetzt installieren?\n\n(Optional — kann auch später nachgeholt werden\n via Re-Run dieses firstboot.sh.)"

            # --- Finish ---
            T_FINISH_TITLE="Fertig"
            T_FINISH_HEADER="Setup abgeschlossen."
            T_FINISH_TZ="Zeitzone:       "
            T_FINISH_DEFLOC="Default-Locale: "
            T_FINISH_HINT="Bitte einmal 'exit' und neu einloggen,\\ndamit die Locale in der Shell-Session greift."
            ;;
    esac
}

# === Phase 0 — Pre-Flight ===

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "Dieses Skript muss als root laufen."
        err "  Tipp: sudo bash $0"
        err "  Oder:  sudo bash <(curl -s https://ccc.xed.dev/firstboot.sh)"
        exit 1
    fi
}

require_supported_distro() {
    if [ ! -r /etc/os-release ]; then
        err "/etc/os-release nicht lesbar — unbekannte Distro."
        exit 1
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    case "${ID:-}" in
        debian|ubuntu)
            ok "Distro erkannt: ${PRETTY_NAME:-$ID}"
            ;;
        *)
            err "Distro '${ID:-unknown}' nicht unterstützt — nur Debian/Ubuntu."
            exit 1
            ;;
    esac
}

bootstrap_apt() {
    # Skip-Logik: wenn alle Pre-Pakete schon da, kein apt-update + install
    # (spart bei Re-Run typisch 5-15 Sekunden)
    if pkg_is_installed whiptail \
        && pkg_is_installed locales \
        && pkg_is_installed tzdata \
        && pkg_is_installed ca-certificates; then
        ok "Bootstrap-Pakete bereits vorhanden — apt-update übersprungen."
        return 0
    fi

    info "apt-Cache aktualisieren (kann ein paar Sekunden dauern)..."
    apt-get update -qq </dev/null

    info "Bootstrap-Pakete (whiptail, locales, tzdata, ca-certificates) sicherstellen..."
    apt-get install -y -qq --no-install-recommends \
        whiptail locales tzdata ca-certificates </dev/null

    if ! command -v whiptail >/dev/null 2>&1; then
        err "whiptail nicht verfügbar nach Install — Bootstrap fehlgeschlagen."
        exit 1
    fi
    ok "Bootstrap-Pakete bereit."
}

detect_tty() {
    # Process Substitution `bash <(curl ...)` → stdin ist TTY
    # Klassische Pipe `curl ... | bash`        → stdin ist Pipe (kein TTY)
    if [ -t 0 ]; then
        TTY_MODE="interactive"
        info "TTY erkannt — interaktive Whiptail-Dialoge aktiv."
    else
        TTY_MODE="noninteractive"
        info "Kein TTY (Pipe-Modus) — non-interactive mit ENV-Defaults."
    fi
}

# === Phase 1 — Eingaben sammeln ===

collect_inputs_interactive() {
    # State-Machine mit <Zurück>-Support: Cancel-Button = "Zurück" (außer Phase 1).
    # Sechs Phasen: 1=Sprache, 2=TZ, 3=Locales, 4=Default-Locale, 5=Pakete, 6=Confirm.
    # Bei Cancel/Esc → Phase decrement; in Phase 1 → Abort-Confirmation.

    init_strings   # vorab DE als Fallback laden (Phase-1-Abort-Dialog)

    local PHASE=1
    local MAX_PHASE=6
    local rc

    while [ "$PHASE" -le "$MAX_PHASE" ]; do
        rc=0
        case $PHASE in
            1)
                # --- Phase 1: Sprache ---
                # Kein --cancel-button "Zurück" weil keine Vorgänger-Phase.
                # Cancel/Esc → Abort-Confirmation.
                LANG_CHOICE=$(whiptail --title "Sprache / Language" \
                    --menu "Sprache wählen / Choose language" \
                    12 60 2 \
                    "DE" "Deutsch" \
                    "EN" "English" \
                    3>&1 1>&2 2>&3) || rc=$?
                if [ "$rc" -eq 0 ]; then
                    init_strings   # Strings für gewählte Sprache laden
                fi
                ;;

            2)
                # --- Phase 2: Zeitzone ---
                TZ_VALUE=$(whiptail --title "$T_TZ_TITLE" \
                    --cancel-button "$T_BACK" \
                    --menu "$T_TZ_PROMPT" \
                    16 70 5 \
                    "UTC"            "$T_TZ_UTC" \
                    "Europe/Vienna"  "$T_TZ_VIENNA" \
                    "Asia/Nicosia"   "$T_TZ_NICOSIA" \
                    "Europe/Berlin"  "$T_TZ_BERLIN" \
                    "Europe/London"  "$T_TZ_LONDON" \
                    3>&1 1>&2 2>&3) || rc=$?
                ;;

            3)
                # --- Phase 3: Locales (Multi-Select, mit Idempotenz-Erkennung) ---
                LOCALES_VALUE=$(whiptail --title "$T_LOC_TITLE" \
                    --cancel-button "$T_BACK" \
                    --checklist "$T_LOC_PROMPT" \
                    18 65 8 \
                    "de_AT.UTF-8" "$T_LOC_AT" "$(locale_state de_AT.UTF-8 ON)"  \
                    "de_DE.UTF-8" "$T_LOC_DE" "$(locale_state de_DE.UTF-8 ON)"  \
                    "de_CH.UTF-8" "$T_LOC_CH" "$(locale_state de_CH.UTF-8 ON)"  \
                    "en_US.UTF-8" "$T_LOC_US" "$(locale_state en_US.UTF-8 ON)"  \
                    "en_GB.UTF-8" "$T_LOC_GB" "$(locale_state en_GB.UTF-8 ON)"  \
                    "fr_FR.UTF-8" "$T_LOC_FR" "$(locale_state fr_FR.UTF-8 OFF)" \
                    "it_IT.UTF-8" "$T_LOC_IT" "$(locale_state it_IT.UTF-8 OFF)" \
                    "es_ES.UTF-8" "$T_LOC_ES" "$(locale_state es_ES.UTF-8 OFF)" \
                    3>&1 1>&2 2>&3) || rc=$?
                if [ "$rc" -eq 0 ]; then
                    LOCALES_VALUE=$(echo "$LOCALES_VALUE" | tr -d '"')
                    if [ -z "$LOCALES_VALUE" ]; then
                        whiptail --title "$T_LOC_NONE_TITLE" --msgbox "$T_LOC_NONE" 8 60
                        continue   # nochmal Phase 3
                    fi
                fi
                ;;

            4)
                # --- Phase 4: Default-Locale (dynamisch, Layout-Fix, idempotent) ---
                local default_args=()
                local locale_count=0
                for loc in $LOCALES_VALUE; do
                    default_args+=("$loc" "")
                    locale_count=$((locale_count + 1))
                done
                local box_height=$((locale_count + 8))
                [ "$box_height" -lt 12 ] && box_height=12

                local current_default
                current_default=$(current_default_locale)
                local default_item_args=()
                if [ -n "$current_default" ] && echo "$LOCALES_VALUE" | grep -qw "$current_default"; then
                    default_item_args+=(--default-item "$current_default")
                fi

                DEFAULT_LOCALE_VALUE=$(whiptail --title "$T_DEFLOC_TITLE" \
                    --cancel-button "$T_BACK" \
                    "${default_item_args[@]}" \
                    --menu "$T_DEFLOC_PROMPT" \
                    "$box_height" 60 "$locale_count" \
                    "${default_args[@]}" \
                    3>&1 1>&2 2>&3) || rc=$?
                ;;

            5)
                # --- Phase 5: Pakete (mit Idempotenz-Erkennung) ---
                PKGS_VALUE=$(whiptail --title "$T_PKGS_TITLE" \
                    --cancel-button "$T_BACK" \
                    --checklist "$T_PKGS_PROMPT" \
                    20 70 12 \
                    "htop"          "$T_PKG_HTOP"     "$(pkg_state htop ON)" \
                    "curl"          "$T_PKG_CURL"     "$(pkg_state curl ON)" \
                    "wget"          "$T_PKG_WGET"     "$(pkg_state wget ON)" \
                    "sudo"          "$T_PKG_SUDO"     "$(pkg_state sudo ON)" \
                    "psmisc"        "$T_PKG_PSMISC"   "$(pkg_state psmisc ON)" \
                    "net-tools"     "$T_PKG_NETTOOLS" "$(pkg_state net-tools ON)" \
                    "iproute2"      "$T_PKG_IPROUTE2" "$(pkg_state iproute2 ON)" \
                    "iputils-ping"  "$T_PKG_IPING"    "$(pkg_state iputils-ping ON)" \
                    "gnupg"         "$T_PKG_GNUPG"    "$(pkg_state gnupg ON)" \
                    "nano"          "$T_PKG_NANO"     "$(pkg_state nano ON)" \
                    "pwgen"         "$T_PKG_PWGEN"    "$(pkg_state pwgen OFF)" \
                    "socat"         "$T_PKG_SOCAT"    "$(pkg_state socat OFF)" \
                    3>&1 1>&2 2>&3) || rc=$?
                if [ "$rc" -eq 0 ]; then
                    PKGS_VALUE=$(echo "$PKGS_VALUE" | tr -d '"')
                fi
                ;;

            6)
                # --- Phase 6: Bestätigung ---
                # yesno-Dialog: --no-button als Zurück-Pendant ($T_APPLY = Yes)
                whiptail --title "$T_CONFIRM_TITLE" \
                    --yes-button "$T_APPLY" \
                    --no-button "$T_BACK" \
                    --yesno \
"$T_CONFIRM_TZ$TZ_VALUE
$T_CONFIRM_LOCALES$LOCALES_VALUE
$T_CONFIRM_DEFLOC$DEFAULT_LOCALE_VALUE
$T_CONFIRM_PKGS$PKGS_VALUE

$T_CONFIRM_PROMPT" 18 70 || rc=$?
                ;;
        esac

        if [ "$rc" -eq 0 ]; then
            PHASE=$((PHASE + 1))
        else
            # Cancel/Esc = Zurück
            if [ "$PHASE" -le 1 ]; then
                # In Phase 1 ist „Zurück" = Abort-Confirmation
                if whiptail --title "$T_ABORT_TITLE" --yesno "$T_ABORT_PROMPT" 8 60; then
                    info "Abgebrochen."
                    exit 1
                fi
                # else: bleibe in Phase 1
            else
                PHASE=$((PHASE - 1))
            fi
        fi
    done
}

collect_inputs_noninteractive() {
    init_strings   # T_-Strings auch im non-interactive-Pfad setzen (für apply_packages, finish, etc.)

    TZ_VALUE="${TZ:-UTC}"
    LOCALES_VALUE="${LOCALES:-de_AT.UTF-8 en_US.UTF-8}"
    DEFAULT_LOCALE_VALUE="${DEFAULT_LOCALE:-de_AT.UTF-8}"
    PKGS_VALUE="${PKGS:-htop curl wget sudo psmisc net-tools iproute2 iputils-ping gnupg nano}"

    info "Non-interactive Defaults:"
    info "  Zeitzone:        $TZ_VALUE"
    info "  Locales:         $LOCALES_VALUE"
    info "  Default-Locale:  $DEFAULT_LOCALE_VALUE"
    info "  Pakete:          $PKGS_VALUE"
}

# === Phase 2 — Zeitzone ===

apply_timezone() {
    info "Zeitzone setzen: $TZ_VALUE"
    if [ ! -e "/usr/share/zoneinfo/$TZ_VALUE" ]; then
        err "Unbekannte Zeitzone: $TZ_VALUE (/usr/share/zoneinfo/$TZ_VALUE existiert nicht)"
        exit 1
    fi
    ln -fs "/usr/share/zoneinfo/$TZ_VALUE" /etc/localtime
    echo "$TZ_VALUE" > /etc/timezone
    dpkg-reconfigure -f noninteractive tzdata </dev/null >/dev/null 2>&1
    ok "Zeitzone: $(cat /etc/timezone) ($(date +%Z))"
}

# === Phase 3 — Locales ===

apply_locales() {
    # Diff-Logik analog apply_packages:
    #   to_enable  = in LOCALES_VALUE, aber nicht aktiv in /etc/locale.gen
    #   to_disable = in LOCALE_MENU_LIST + aktiv, aber nicht in LOCALES_VALUE
    #                (nur Menü-Locales — User-eigene Custom-Locales bleiben unangetastet)
    local to_enable=""
    local to_disable=""
    local loc pattern

    for loc in $LOCALES_VALUE; do
        if ! locale_is_active "$loc"; then
            to_enable="$to_enable $loc"
        fi
    done

    for loc in $LOCALE_MENU_LIST; do
        if locale_is_active "$loc"; then
            if ! echo " $LOCALES_VALUE " | grep -qw "$loc"; then
                to_disable="$to_disable $loc"
            fi
        fi
    done

    # --- Enable-Phase (uncomment + bei Bedarf append) ---
    if [ -n "${to_enable// /}" ]; then
        info "Locales aktivieren:$to_enable"
        for loc in $to_enable; do
            pattern="${loc//./\\.}"
            if grep -qE "^#?[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null; then
                # vorhanden (commented) — uncomment
                sed -i "s/^# *\\(${pattern}[[:space:]]\\+UTF-8\\)/\\1/" /etc/locale.gen
            else
                # nicht in /etc/locale.gen vorhanden — append
                echo "$loc UTF-8" >> /etc/locale.gen
            fi
        done
    else
        info "Alle gewünschten Locales bereits aktiv — kein Enable."
    fi

    # --- Disable-Phase (comment-out, kein extra-Confirm — User-Wille im Menü ist klar) ---
    if [ -n "${to_disable// /}" ]; then
        info "Locales deaktivieren:$to_disable"
        for loc in $to_disable; do
            pattern="${loc//./\\.}"
            # Nur uncommented-Zeilen kommentieren; bereits commented-Zeilen sind no-op
            sed -i "s/^\\(${pattern}[[:space:]]\\+UTF-8\\)/# \\1/" /etc/locale.gen
        done
    fi

    locale-gen </dev/null >/dev/null 2>&1
    update-locale LANG="$DEFAULT_LOCALE_VALUE" LC_CTYPE="$DEFAULT_LOCALE_VALUE"
    ok "Default-Locale gesetzt: $DEFAULT_LOCALE_VALUE (in /etc/default/locale)"
}

# === Phase 4 — Pakete ===

apply_packages() {
    # Diff-Logik:
    #   to_install = in PKGS_VALUE, aber nicht installiert
    #   to_remove  = in PKG_MENU_LIST + installiert, aber nicht in PKGS_VALUE
    #                (nur Menü-Pakete kommen für Deinstallation in Frage —
    #                Schutzschicht gegen System-Pakete)
    local to_install=""
    local to_remove=""
    local pkg

    for pkg in $PKGS_VALUE; do
        if ! pkg_is_installed "$pkg"; then
            to_install="$to_install $pkg"
        fi
    done

    for pkg in $PKG_MENU_LIST; do
        if pkg_is_installed "$pkg"; then
            if ! echo " $PKGS_VALUE " | grep -qw "$pkg"; then
                to_remove="$to_remove $pkg"
            fi
        fi
    done

    # --- Install-Phase ---
    if [ -n "${to_install// /}" ]; then
        info "Pakete installieren (--no-install-recommends):$to_install"
        # shellcheck disable=SC2086
        apt-get install -y -qq --no-install-recommends $to_install </dev/null
        ok "Pakete installiert."
    else
        info "Alle gewünschten Pakete bereits installiert — kein Install."
    fi

    # --- Remove-Phase (nur mit explizitem User-Yes) ---
    if [ -n "${to_remove// /}" ]; then
        local confirm_remove="no"
        if [ "$TTY_MODE" = "interactive" ]; then
            if whiptail --title "$T_REMOVE_TITLE" --yesno \
"$T_REMOVE_PROMPT_PRE

$to_remove

$T_REMOVE_PROMPT_POST" \
                15 65; then
                confirm_remove="yes"
            fi
        else
            # Non-interactive: opt-in via ENV REMOVE_DESELECTED=yes
            if [ "${REMOVE_DESELECTED:-no}" = "yes" ]; then
                confirm_remove="yes"
            fi
        fi

        if [ "$confirm_remove" = "yes" ]; then
            info "Pakete deinstallieren:$to_remove"
            # shellcheck disable=SC2086
            apt-get remove -y -qq $to_remove </dev/null
            ok "Pakete deinstalliert."
        else
            info "Deinstallation übersprungen — abgewählte Pakete bleiben."
        fi
    fi
}

# === Phase 5b — apt dist-upgrade-Prompt ===

apply_dist_upgrade_prompt() {
    info "Prüfe verfügbare Pakete-Updates..."
    # apt list --upgradable spuckt eine Header-Zeile + N Pakete-Zeilen
    local upgradable
    upgradable=$(apt list --upgradable 2>/dev/null | tail -n +2 | grep -c '/' || true)

    if [ "$upgradable" -eq 0 ]; then
        ok "Keine Pakete-Updates verfügbar — System ist aktuell."
        return 0
    fi

    info "$upgradable Pakete-Updates verfügbar."

    local confirm="no"
    if [ "$TTY_MODE" = "interactive" ]; then
        if whiptail --title "$T_UPGRADE_TITLE" --yesno \
"$upgradable $T_UPGRADE_PROMPT_PRE

$T_UPGRADE_PROMPT_POST" \
            14 65; then
            confirm="yes"
        fi
    else
        # Non-interactive: opt-in via ENV DIST_UPGRADE=yes für Auto-Run
        if [ "${DIST_UPGRADE:-no}" = "yes" ]; then
            confirm="yes"
        fi
    fi

    if [ "$confirm" = "yes" ]; then
        info "apt dist-upgrade ausführen..."
        apt-get dist-upgrade -y -qq </dev/null
        ok "Updates installiert."
        info "apt autoremove (verwaiste Dependencies entfernen)..."
        apt-get autoremove -y -qq </dev/null
        info "apt autoclean (alten Paket-Cache löschen)..."
        apt-get autoclean -qq </dev/null
        ok "System aufgeräumt."
    else
        info "Updates übersprungen — System bleibt auf aktuellem Stand."
    fi
}

# === Phase 5 — EDITOR ===

apply_editor() {
    info "EDITOR=nano in /etc/environment sicherstellen..."
    if grep -q '^EDITOR=' /etc/environment 2>/dev/null; then
        local current
        current=$(grep '^EDITOR=' /etc/environment | head -1)
        info "  bereits vorhanden: $current — kein Append."
    else
        echo 'EDITOR=nano' >> /etc/environment
        ok "  EDITOR=nano hinzugefügt."
    fi
}

# === Phase 6 — Abschluss ===

# === Phase 7 — XED /CCC Python-Tool-Installation (pipx-basiert ab v0.8.0) ===
#
# pipx-basierte CLI-Tool-Distribution: jedes Tool in eigener venv unter
# /opt/pipx/venvs/, mit Symlink in /usr/local/bin/. Mainstream-Pattern für
# CLI-Tool-Distribution (uv, ruff, black, yt-dlp).
#
# Updates:   pipx upgrade xed-ccc xed-cca
# Self-Heal: pipx reinstall xed-ccc / xed-cca
#
# Migration v0.7.x -> v0.8.x: alte Symlinks /usr/local/bin/{ccc,cca} werden
# nach .replaced.<timestamp> umbenannt (no-rm-Disziplin); alte
# /opt/xed-ccc + /opt/xed-cca Verzeichnisse bleiben liegen, manueller
# Cleanup durch DevOps wenn gewünscht.
#
# Pattern: reference_pipx_for_cli_tools.md (AI036, 2026-05-04).

# Cascade-Schutz für apt purge: Hard-Deps werden automatisch mit-entfernt;
# bei system-critical Meta-Paketen (z.B. vanilla-gnome-desktop, ubuntu-minimal)
# zerstört das den Stack. Pattern: simulate -> cascade parsen -> Whitelist-Check
# -> nur dann purgen.
#
# Argument: $1 = Paket-Liste (Space-separated, ungequotet wegen apt-get-Syntax).
# Return: 0 = purge ausgefuehrt (oder no-op), 1 = abort wegen Whitelist-Verletzung.
safe_purge() {
    local pkgs="$1"
    local cascade
    # shellcheck disable=SC2086
    cascade=$(apt-get purge --simulate -y $pkgs 2>/dev/null \
              | awk '/^Remv / {print $2}')

    local crit
    for crit in "${CRITICAL_PACKAGES_WHITELIST[@]}"; do
        if echo "$cascade" | grep -qx "$crit"; then
            err "ABORT safe_purge: cascade entfernt kritisches Paket: $crit"
            err "  Vollstaendige Cascade:"
            echo "$cascade" | while read -r p; do err "    - $p"; done
            err "  Skript-Fix noetig: Paket-Liste reduzieren ODER Whitelist anpassen."
            err "  Recovery: kein automatischer Purge, '$pkgs' bleibt installiert."
            return 1
        fi
    done

    info "safe_purge cleared (cascade: $(echo "$cascade" | tr '\n' ' '))"
    # shellcheck disable=SC2086
    apt-get purge -y -qq $pkgs 2>/dev/null || true
    return 0
}

# Ubuntu-Pro-Werbung non-destruktiv deaktivieren.
# Mainstream-Pfad statt destruktivem purge: pro CLI + APT-Hook-mv + systemd.
# Doku: documentation.ubuntu.com/pro-client/howtoguides/disable_enable_apt_news/
self_heal_pro_notice() {
    info "Self-Heal: Ubuntu-Pro-Werbung deaktivieren (Community-Only, non-destruktiv)..."

    # A — pro CLI (offizieller Pfad ab Pro-Client v30)
    if command -v pro >/dev/null 2>&1; then
        pro config set apt_news=false 2>&1 \
            | tee -a "${FIRSTBOOT_LOG_FILE:-/dev/null}" || true
    fi

    # B — ESM-APT-Hook deaktivieren via mv (no-deletion-konform, reversibel)
    if [ -f /etc/apt/apt.conf.d/20apt-esm-hook.conf ]; then
        mv /etc/apt/apt.conf.d/20apt-esm-hook.conf \
           /etc/apt/apt.conf.d/20apt-esm-hook.conf.bak
        info "ESM-APT-Hook deaktiviert: 20apt-esm-hook.conf -> .bak"
    fi

    # C — apt-news.service deaktivieren wenn vorhanden
    systemctl disable --now apt-news.service 2>/dev/null || true
}

# Self-Heal vor apt-Aufrufen. Idempotent: no-op auf sauberem System.
# Snap-Redirect-Pakete in LXC unzuverlaessig (snapd-Bugs); safe_purge()
# schuetzt vor Cascade-Removes von Meta-Paketen.
# Pattern: reference_no_snap_in_lxc.md.
self_heal_dpkg() {
    info "Self-Heal: snap-Redirect-Pakete entfernen (LXC-Kompatibilitaet, mit Cascade-Schutz)..."
    safe_purge "$SNAP_REDIRECT_PACKAGES_LIST" || true

    info "Self-Heal: dpkg --configure -a..."
    dpkg --configure -a 2>/dev/null || true

    info "Self-Heal: apt-get install -f..."
    apt-get install -f -y -qq </dev/null

    info "Self-Heal: apt-get autoremove --purge..."
    apt-get autoremove --purge -y -qq </dev/null
}

# Migration alter Symlink (v0.7.x git+venv -> v0.8.x pipx).
# Wenn ein Symlink nicht auf $PIPX_HOME_DIR zeigt, umbenennen via mv-replaced.
# Idempotent: no-op wenn Symlink schon auf pipx-Pfad zeigt.
migrate_old_symlink() {
    local link="$1"
    if [ -L "$link" ]; then
        local target
        target=$(readlink -f "$link" 2>/dev/null || echo "")
        case "$target" in
            "${PIPX_HOME_DIR}"/*) ;;
            "")
                local ts
                ts=$(date +%Y%m%d-%H%M%S)
                mv "$link" "${link}.replaced.${ts}"
                info "Defekten Symlink umbenannt: ${link}.replaced.${ts}"
                ;;
            *)
                local ts
                ts=$(date +%Y%m%d-%H%M%S)
                mv "$link" "${link}.replaced.${ts}"
                info "Alter Symlink umbenannt: ${link}.replaced.${ts}"
                ;;
        esac
    fi
}

apply_ccc_installation() {
    local confirm="no"
    if [ "$TTY_MODE" = "interactive" ]; then
        if whiptail --title "$T_CCC_TITLE" --yesno "$T_CCC_PROMPT" 20 65; then
            confirm="yes"
        fi
    else
        # Non-interactive: opt-in via ENV LAUNCH_CCC=yes
        if [ "${LAUNCH_CCC:-no}" = "yes" ]; then
            confirm="yes"
        fi
    fi

    if [ "$confirm" != "yes" ]; then
        info "XED /CCC Python-Tool übersprungen — späterer Re-Run von firstboot.sh möglich."
        return 0
    fi

    # --- Schritt 0: Self-Heal vor jedem apt-Aufruf (dpkg + Pro-Notice) ---
    self_heal_dpkg
    self_heal_pro_notice

    # --- Schritt 1: pipx via apt ---
    info "pipx installieren (apt)..."
    apt-get install -y -qq pipx </dev/null
    ok "pipx bereit: $(pipx --version 2>&1)"

    # --- Schritt 2: System-wide pipx-Setup via env-vars ---
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    # --- Schritt 3: Migration alter Symlink (v0.7.x -> v0.8.x) ---
    migrate_old_symlink "$CCC_BIN_LINK"

    # --- Schritt 4: pipx install/upgrade (idempotent) ---
    info "xed-ccc via pipx installieren/aktualisieren..."
    if pipx list --short 2>/dev/null | grep -q '^xed-ccc '; then
        pipx upgrade xed-ccc
    else
        pipx install xed-ccc
    fi

    # --- Schritt 5: PATH-Fix (zwei Stellen für volle Shell-Abdeckung) ---
    # Bleibt zwingend drin: pct-enter-Falle ist unabhängig von pipx.
    # `pct enter` startet eine NON-LOGIN interactive bash mit minimal-PATH
    # (/sbin:/bin:/usr/sbin:/usr/bin) ohne /usr/local/bin. Daher braucht
    # /etc/bash.bashrc den PATH-Fix. Profile.d zusätzlich für Login-Shells.
    cat > /etc/profile.d/xed-ccc.sh <<'EOF'
# XED-CCC: stelle sicher dass /usr/local/bin im PATH ist (Login-Shells).
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
    chmod 0644 /etc/profile.d/xed-ccc.sh
    info "PATH-Fix Login-Shells: /etc/profile.d/xed-ccc.sh"

    # /etc/bash.bashrc-Append (interactive non-login bash, z.B. pct enter)
    if ! grep -q '# XED-CCC PATH-Fix' /etc/bash.bashrc 2>/dev/null; then
        cat >> /etc/bash.bashrc <<'EOF'

# XED-CCC PATH-Fix (interactive non-login bash, z.B. pct enter)
# Login-Shells nutzen /etc/profile.d/xed-ccc.sh
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
        info "PATH-Fix interactive bash: /etc/bash.bashrc-Append"
    else
        info "PATH-Fix /etc/bash.bashrc-Block bereits vorhanden — kein Append."
    fi

    # --- Schritt 6: Smoke-Test ---
    if "$CCC_BIN_LINK" --version >/dev/null 2>&1; then
        ok "ccc installiert: $($CCC_BIN_LINK --version 2>&1 | head -1)"
    else
        err "ccc installiert via pipx, aber 'ccc --version' liefert non-zero."
        err "  ls -la $CCC_BIN_LINK"
        err "  pipx list"
        return 1
    fi

    info "Nächste Schritte (nach 'exit' und neu einloggen für PATH-Wirksamkeit):"
    info "  ccc --help              # alle Verben"
    info "  ccc list                # verfügbare Rollen"
    info "  ccc create pmDESK       # Beispiel: Gnome-Desktop installieren"
    info ""
    info "Updates:    pipx upgrade xed-ccc"
    info "Self-Heal:  pipx reinstall xed-ccc"
}

# === Phase 7b — XED /CCA App-Tool-Installation (pipx-basiert ab v0.8.0) ===
#
# Läuft NUR wenn ccc bereits installiert ist (User hat im Phase-7-Yesno
# „yes" gewählt). Beide Tools werden zusammen installiert oder gar nicht.
# pipx-Stack ist bereits durch Phase 7 installiert, daher kein apt hier.

apply_cca_installation() {
    # Skip wenn ccc nicht installiert (= User hat in Phase 7 No gewählt)
    if [ ! -L "$CCC_BIN_LINK" ] && [ ! -x "$CCC_BIN_LINK" ]; then
        info "ccc nicht installiert — überspringe cca-Installation."
        return 0
    fi

    info "==============================================================="
    info "  Phase 7b: cca (App-Tool) installieren"
    info "==============================================================="

    # --- Schritt 1: pipx-Setup (gleicher PIPX_HOME wie Phase 7) ---
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    # --- Schritt 2: Migration alter Symlink (v0.7.x -> v0.8.x) ---
    migrate_old_symlink "$CCA_BIN_LINK"

    # --- Schritt 3: pipx install/upgrade (idempotent) ---
    info "xed-cca via pipx installieren/aktualisieren..."
    if pipx list --short 2>/dev/null | grep -q '^xed-cca '; then
        pipx upgrade xed-cca
    else
        pipx install xed-cca
    fi

    # --- Schritt 4: Smoke-Test ---
    if "$CCA_BIN_LINK" --version >/dev/null 2>&1; then
        ok "cca installiert: $($CCA_BIN_LINK --version 2>&1 | head -1)"
    else
        err "cca installiert via pipx, aber 'cca --version' liefert non-zero."
        return 1
    fi

    info "Verfügbar nach 'exit' und neu einloggen:"
    info "  cca --help              # alle Verben"
    info "  cca list                # verfügbare Apps"
    info "  cca install gnome       # Beispiel: Vanilla Gnome installieren"
    info ""
    info "Updates:    pipx upgrade xed-cca"
    info "Self-Heal:  pipx reinstall xed-cca"
}

# === Phase 8 — Abschluss ===

finish() {
    local lang_line
    lang_line=$(grep '^LANG=' /etc/default/locale 2>/dev/null | cut -d= -f2 || echo "?")

    local msg
    msg="$T_FINISH_HEADER

$T_FINISH_TZ$(cat /etc/timezone)
$T_FINISH_DEFLOC${lang_line}

$(echo -e "$T_FINISH_HINT")"

    if [ "$TTY_MODE" = "interactive" ]; then
        whiptail --title "$T_FINISH_TITLE" --msgbox "$msg" 14 60
    else
        echo
        echo "------------------------------------------------------------"
        echo "$msg"
        echo "------------------------------------------------------------"
    fi
}

# === Main ===

main() {
    banner
    require_root
    init_log_file
    require_supported_distro
    bootstrap_apt
    detect_tty

    if [ "$TTY_MODE" = "interactive" ]; then
        collect_inputs_interactive
    else
        collect_inputs_noninteractive
    fi

    apply_timezone
    apply_locales
    apply_packages
    apply_dist_upgrade_prompt
    apply_editor

    # Phase 7+7b: Log-Konservierung für Support. info/ok/err/warn schreiben
    # bei gesetztem $PHASE_LOG_FILE zusätzlich dorthin. Am Ende: msgbox.
    PHASE_LOG_FILE="/tmp/xed-firstboot-phase7-$$.log"
    : > "$PHASE_LOG_FILE"

    apply_ccc_installation
    apply_cca_installation

    if [ "$TTY_MODE" = "interactive" ] && [ -s "$PHASE_LOG_FILE" ]; then
        whiptail --title "Phase 7 + 7b — Installations-Log" \
                 --scrolltext \
                 --msgbox "$(cat "$PHASE_LOG_FILE")" 30 80 || true
    fi
    unset PHASE_LOG_FILE

    finish

    # Marker-Datei: signalisiert "erster Run abgeschlossen" für künftige
    # Re-Runs (is_first_run() == false → User-Wille respektieren statt
    # Skript-Defaults bei pre-Select).
    mkdir -p "$(dirname "$FIRSTBOOT_MARKER")"
    touch "$FIRSTBOOT_MARKER"

    ok "${SCRIPT_NAME} durchgelaufen — Box bereit."

    # Hint-Block: Audit-Log-Pfad + Lese-Beispiele für SysOps/DevOps/AI-Agent.
    # Wartungs-Pfad sichtbar machen — Logs sind A+O des Developer-Lebens.
    echo
    info "Audit-Log dieses Runs: ${FIRSTBOOT_LOG_FILE}"
    info "  tail -50 ${FIRSTBOOT_LOG_FILE}             # letzte 50 Zeilen"
    info "  less ${FIRSTBOOT_LOG_FILE}                 # vollstaendig durchblaettern"
    info "  grep ERROR ${FIRSTBOOT_LOG_FILE}           # nur Fehler-Zeilen"
    info "  grep WARN ${FIRSTBOOT_LOG_FILE}            # nur Warnungen"
    echo
}

main "$@"
