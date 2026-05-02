#!/bin/bash
# firstboot.sh — XED-CCC Bash-Basis-Setup für frische Debian/Ubuntu-Boxen
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

VERSION="0.2.0"
SCRIPT_NAME="firstboot.sh"
TTY_MODE=""

# Konfigurations-Variablen, gefüllt durch Phase 1
TZ_VALUE=""
LOCALES_VALUE=""
DEFAULT_LOCALE_VALUE=""
PKGS_VALUE=""

# === Output-Helpers ===

banner() {
    echo
    echo "========================================================================"
    echo "  XED-CCC ${SCRIPT_NAME} v${VERSION}"
    echo "  Basis-Setup für frische Debian/Ubuntu-LXC-Boxen"
    echo "========================================================================"
    echo
}

err()  { echo "ERROR: $*" >&2; }
info() { echo "→ $*"; }
ok()   { echo "✔ $*"; }
warn() { echo "⚠ $*" >&2; }

# === Idempotenz-Helper ===

# Ist Locale (z.B. "de_AT.UTF-8") in /etc/locale.gen UNcommented?
locale_is_active() {
    local loc="$1"
    local pattern="${loc//./\\.}"
    grep -qE "^[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null
}

# Ist Paket installiert? (dpkg-query)
pkg_is_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

# Liefert "ON" wenn Item bereits aktiv (idempotent), sonst $default ("ON"/"OFF")
locale_state() {
    if locale_is_active "$1"; then echo "ON"; else echo "$2"; fi
}
pkg_state() {
    if pkg_is_installed "$1"; then echo "ON"; else echo "$2"; fi
}

# Aktueller System-Default-Locale (für `whiptail --default-item`)
current_default_locale() {
    if [ -r /etc/default/locale ]; then
        grep '^LANG=' /etc/default/locale 2>/dev/null | cut -d= -f2 | tr -d '"'
    fi
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
    info "apt-Cache aktualisieren..."
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
    # --- Zeitzone ---
    TZ_VALUE=$(whiptail --title "Server-Zeitzone" \
        --menu "Empfehlung: UTC für Server. Lokale Zeit besser pro User-Shell setzen." \
        16 70 5 \
        "UTC"            "Empfohlen — keine DST-Sprünge, saubere Logs" \
        "Europe/Vienna"  "DACH-Standard (CET/CEST)" \
        "Asia/Nicosia"   "Cyprus / EET (DevOps-Standort)" \
        "Europe/Berlin"  "Generisch DACH" \
        "Europe/London"  "UK / GMT" \
        3>&1 1>&2 2>&3) || { info "Abgebrochen."; exit 1; }

    # --- Locales (Multi-Select, mit Idempotenz-Erkennung) ---
    # Pre-selected: aktuell aktive Locales aus /etc/locale.gen + Skript-Defaults
    # Default-ON jetzt: AT, DE, CH, US, GB (DevOps-Wunsch)
    LOCALES_VALUE=$(whiptail --title "Locales generieren" \
        --checklist "Welche Locales sollen verfügbar sein? (Leertaste = toggle)" \
        18 65 8 \
        "de_AT.UTF-8" "Österreich"   "$(locale_state de_AT.UTF-8 ON)"  \
        "de_DE.UTF-8" "Deutschland"  "$(locale_state de_DE.UTF-8 ON)"  \
        "de_CH.UTF-8" "Schweiz"      "$(locale_state de_CH.UTF-8 ON)"  \
        "en_US.UTF-8" "US-Englisch"  "$(locale_state en_US.UTF-8 ON)"  \
        "en_GB.UTF-8" "UK-Englisch"  "$(locale_state en_GB.UTF-8 ON)"  \
        "fr_FR.UTF-8" "Frankreich"   "$(locale_state fr_FR.UTF-8 OFF)" \
        "it_IT.UTF-8" "Italien"      "$(locale_state it_IT.UTF-8 OFF)" \
        "es_ES.UTF-8" "Spanien"      "$(locale_state es_ES.UTF-8 OFF)" \
        3>&1 1>&2 2>&3) || { info "Abgebrochen."; exit 1; }
    # Whiptail liefert "de_AT.UTF-8" "en_US.UTF-8" mit Quotes — entfernen
    LOCALES_VALUE=$(echo "$LOCALES_VALUE" | tr -d '"')

    if [ -z "$LOCALES_VALUE" ]; then
        err "Keine Locales ausgewählt — Abbruch."
        exit 1
    fi

    # --- Default-Locale (dynamisch aus Auswahl, Layout-Fix) ---
    local default_args=()
    local locale_count=0
    for loc in $LOCALES_VALUE; do
        default_args+=("$loc" "")
        locale_count=$((locale_count + 1))
    done
    # Box-Höhe = locale_count + 8 (Border + Title + Message + Buttons-Zeile)
    local box_height=$((locale_count + 8))
    [ "$box_height" -lt 12 ] && box_height=12

    # Aktuell aktive Default-Locale als pre-selected markieren (idempotent)
    local current_default
    current_default=$(current_default_locale)
    local default_item_args=()
    if [ -n "$current_default" ] && echo "$LOCALES_VALUE" | grep -qw "$current_default"; then
        default_item_args+=(--default-item "$current_default")
    fi

    DEFAULT_LOCALE_VALUE=$(whiptail --title "Default-Locale" \
        "${default_item_args[@]}" \
        --menu "Welche dieser Locales als System-Default (LANG)?" \
        "$box_height" 60 "$locale_count" \
        "${default_args[@]}" \
        3>&1 1>&2 2>&3) || { info "Abgebrochen."; exit 1; }

    # --- Pakete (mit Idempotenz-Erkennung) ---
    # Pre-selected: bereits installierte Pakete + Skript-Defaults
    PKGS_VALUE=$(whiptail --title "Basis-Pakete" \
        --checklist "Welche Tools installieren? (Leertaste = toggle)" \
        20 65 12 \
        "htop"          "Prozess-Monitor"          "$(pkg_state htop ON)" \
        "curl"          "HTTP-Client"              "$(pkg_state curl ON)" \
        "wget"          "HTTP-Downloader"          "$(pkg_state wget ON)" \
        "sudo"          "Privilege-Wechsel"        "$(pkg_state sudo ON)" \
        "psmisc"        "killall, fuser, pstree"   "$(pkg_state psmisc ON)" \
        "net-tools"     "ifconfig, route, netstat" "$(pkg_state net-tools ON)" \
        "iproute2"      "ip a, ip r, ss"           "$(pkg_state iproute2 ON)" \
        "iputils-ping"  "ping"                     "$(pkg_state iputils-ping ON)" \
        "gnupg"         "GPG für Repos"            "$(pkg_state gnupg ON)" \
        "nano"          "Editor"                   "$(pkg_state nano ON)" \
        "pwgen"         "Passwort-Generator"       "$(pkg_state pwgen OFF)" \
        "socat"         "Universal-Socket-Tool"    "$(pkg_state socat OFF)" \
        3>&1 1>&2 2>&3) || { info "Abgebrochen."; exit 1; }
    PKGS_VALUE=$(echo "$PKGS_VALUE" | tr -d '"')

    # --- Bestätigung ---
    whiptail --title "Übersicht — bitte prüfen" --yesno \
"Zeitzone:        $TZ_VALUE
Locales:         $LOCALES_VALUE
Default-Locale:  $DEFAULT_LOCALE_VALUE
Pakete:          $PKGS_VALUE

Anwenden?" 18 70 || { info "Abgebrochen."; exit 1; }
}

collect_inputs_noninteractive() {
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
    info "Locales generieren: $LOCALES_VALUE"
    for loc in $LOCALES_VALUE; do
        # Pattern für sed: Punkte escapen
        local pattern="${loc//./\\.}"
        if grep -qE "^#?[[:space:]]*${pattern}[[:space:]]+UTF-8" /etc/locale.gen 2>/dev/null; then
            # vorhanden (commented oder uncommented) — uncomment
            sed -i "s/^# *\\(${pattern}[[:space:]]\\+UTF-8\\)/\\1/" /etc/locale.gen
        else
            # nicht in /etc/locale.gen vorhanden — append
            echo "$loc UTF-8" >> /etc/locale.gen
        fi
    done

    locale-gen </dev/null >/dev/null 2>&1
    update-locale LANG="$DEFAULT_LOCALE_VALUE" LC_CTYPE="$DEFAULT_LOCALE_VALUE"
    ok "Default-Locale gesetzt: $DEFAULT_LOCALE_VALUE (in /etc/default/locale)"
}

# === Phase 4 — Pakete ===

apply_packages() {
    info "Pakete installieren (--no-install-recommends): $PKGS_VALUE"
    # Intentional word-splitting für Paket-Liste in $PKGS_VALUE
    # shellcheck disable=SC2086
    apt-get install -y -qq --no-install-recommends $PKGS_VALUE </dev/null
    ok "Pakete installiert."
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

finish() {
    local lang_line
    lang_line=$(grep '^LANG=' /etc/default/locale 2>/dev/null | cut -d= -f2 || echo "?")

    local msg
    msg="Setup abgeschlossen.

Zeitzone:        $(cat /etc/timezone)
Default-Locale:  ${lang_line}

Bitte einmal 'exit' und neu einloggen,
damit die Locale in der Shell-Session greift."

    if [ "$TTY_MODE" = "interactive" ]; then
        whiptail --title "Fertig" --msgbox "$msg" 14 60
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
    apply_editor
    finish

    ok "${SCRIPT_NAME} durchgelaufen — Box bereit."
}

main "$@"
