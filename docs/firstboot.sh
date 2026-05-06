#!/bin/bash
# firstboot.sh v0.9.0 — cBOX@ /Container Control Bash-Schmal-Bootstrap
#
# Quelle:    https://github.com/XED-dev/CCC
# Aufruf:    bash <(curl -s https://ccc.xed.dev/firstboot.sh)
# Lokal:     bash firstboot.sh
#
# Was es tut (~150 Zeilen statt 1198 in v0.8.4):
#   Phase 0 — Pre-Flight (root + distro + Audit-Log-Init)
#   Phase 1 — apt install python3-Stack + pipx + Bootstrap-Pakete
#   Phase 2 — pipx install xed-ccc + xed-cca (system-wide via PIPX_HOME)
#   Phase 3 — PATH-Fix (/etc/profile.d + /etc/bash.bashrc, pct-enter-Falle)
#   Phase 4 — exec /usr/local/bin/ccc bootstrap-system "$@"
#
# Phasen 2-7 von v0.8.4 (TZ/Locales/Pakete/Editor/Dist-Upgrade/Confirm) wandern
# in das ccc-Python-Verb 'bootstrap-system'. ENV-Vars (TZ, LOCALES, ...) werden
# via exec durchgereicht. Whiptail-State-Machine + i18n laufen in Python.
#
# Archiv von v0.8.4: scripts/firstboot-v0.8.4.sh.archive (1:1-Snapshot,
# no-deletion-konform, falls jemand v0.8.4-Verhalten reproduzieren muss).
#
# Lizenz: MIT (siehe LICENSE im XED-dev/CCC-Repo)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# === Globals ===

VERSION="0.9.0"
SCRIPT_NAME="firstboot.sh"
FIRSTBOOT_LOG_FILE="/var/log/xed-firstboot.log"

# pipx-System-Setup (env-vars statt --global wegen pipx 1.4.x kompat —
# Pattern: reference_pipx_for_cli_tools.md, AI036 2026-05-04)
PIPX_HOME_DIR="/opt/pipx"
PIPX_BIN_DIR_PATH="/usr/local/bin"

CCC_BIN_LINK="/usr/local/bin/ccc"
CCA_BIN_LINK="/usr/local/bin/cca"

# === Output-Helpers + Audit-Log ===

# Audit-Log-Format identisch zu Python init_audit_log (ccc.system.audit_log):
# '<ISO-UTC> [LEVEL] message' — grep-Pipelines arbeiten ueber Bash- und
# Python-Phasen hinweg auf derselben Datei.
log_to_file() {
    local level="$1"; shift
    [ -n "${FIRSTBOOT_LOG_FILE:-}" ] || return 0
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [$level] $*" >> "$FIRSTBOOT_LOG_FILE" 2>/dev/null || true
}

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

err()  { echo "ERROR: $*" >&2; log_to_file "ERROR" "$*"; }
info() { echo "→ $*"; log_to_file "INFO" "$*"; }
ok()   { echo "✔ $*"; log_to_file "OK" "$*"; }

banner() {
    echo
    echo "================================================================"
    echo "  cBOX@ /Container Control — ${SCRIPT_NAME} v${VERSION}"
    echo "  Bash-Schmal-Bootstrap: Python+pipx+ccc, dann ccc bootstrap-system"
    echo "  cBOX.at/YOU by XED.dev Tools via Collective Context (CC)"
    echo "================================================================"
    echo
}

# === Phase 0 — Pre-Flight ===

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "Skript muss als root laufen. Tipp: sudo bash $0"
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
        debian|ubuntu) ok "Distro erkannt: ${PRETTY_NAME:-$ID}" ;;
        *) err "Distro '${ID:-unknown}' nicht unterstuetzt — nur Debian/Ubuntu."; exit 1 ;;
    esac
}

# === Phase 1 — apt install Python-Stack + Bootstrap-Pakete ===

bootstrap_apt() {
    info "apt update + Python-Stack + pipx + Bootstrap-Pakete installieren..."
    apt-get update -qq </dev/null
    apt-get install -y -qq --no-install-recommends \
        python3 python3-venv git pipx \
        whiptail locales tzdata ca-certificates </dev/null

    if ! command -v pipx >/dev/null 2>&1; then
        err "pipx nicht verfuegbar nach Install — Bootstrap fehlgeschlagen."
        exit 1
    fi
    ok "Python-Stack bereit: pipx $(pipx --version 2>&1 | head -1)"
}

# === Phase 2 — pipx install CC-Suite ===

# Migration alter Symlink (v0.7.x git+venv -> v0.8.x+ pipx).
# Idempotent: no-op wenn Symlink schon auf $PIPX_HOME_DIR zeigt. Sonst
# umbenennen via mv-replaced (no-deletion-konform).
migrate_old_symlink() {
    local link="$1"
    [ -L "$link" ] || return 0
    local target
    target=$(readlink -f "$link" 2>/dev/null || echo "")
    case "$target" in
        "${PIPX_HOME_DIR}"/*) return 0 ;;  # bereits pipx, no-op
        *)
            local ts; ts=$(date +%Y%m%d-%H%M%S)
            mv "$link" "${link}.replaced.${ts}"
            info "Alter/defekter Symlink umbenannt: ${link}.replaced.${ts}"
            ;;
    esac
}

install_cc_suite() {
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    migrate_old_symlink "$CCC_BIN_LINK"
    migrate_old_symlink "$CCA_BIN_LINK"

    # pipx install --force: idempotent ohne pipx-list-Detection-Pattern.
    # Equiv zu upgrade auf neuere Version, no-op auf gleicher Version.
    # Robuster als 'if pipx list --short | grep | upgrade else install',
    # weil unabhängig von pipx-Output-Format-Drift (Senior-Schaerfung
    # AI037 2026-05-06).
    info "xed-ccc via pipx install --force (idempotent)..."
    pipx install --force xed-ccc

    info "xed-cca via pipx install --force (idempotent)..."
    pipx install --force xed-cca

    ok "CC-Suite bereit: ccc + cca via pipx"
}

# === Phase 3 — PATH-Fix (pct-enter-Falle) ===

# pct enter startet NON-LOGIN interactive bash mit minimal-PATH
# (/sbin:/bin:/usr/sbin:/usr/bin) ohne /usr/local/bin. Daher braucht
# /etc/bash.bashrc den PATH-Fix. /etc/profile.d/ zusaetzlich fuer Login-Shells.
# Pattern: reference_path_fix_shell_modes.md (AI035, 2026-05-03).
setup_path_fix() {
    cat > /etc/profile.d/xed-ccc.sh <<'EOF'
# XED-CCC: stelle sicher dass /usr/local/bin im PATH ist (Login-Shells).
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
    chmod 0644 /etc/profile.d/xed-ccc.sh

    if ! grep -q '# XED-CCC PATH-Fix' /etc/bash.bashrc 2>/dev/null; then
        cat >> /etc/bash.bashrc <<'EOF'

# XED-CCC PATH-Fix (interactive non-login bash, z.B. pct enter)
# Login-Shells nutzen /etc/profile.d/xed-ccc.sh
case ":$PATH:" in
    *":/usr/local/bin:"*) ;;
    *) export PATH="/usr/local/bin:$PATH" ;;
esac
EOF
    fi
    ok "PATH-Fix gesetzt (/etc/profile.d + /etc/bash.bashrc)."
}

# === Phase 4 — Hand-off zu ccc bootstrap-system ===

hand_off_to_ccc() {
    if ! "$CCC_BIN_LINK" --version >/dev/null 2>&1; then
        err "ccc nicht aufrufbar: $CCC_BIN_LINK"
        err "  pipx list — Diagnose noetig"
        exit 1
    fi

    info "Hand-off zu 'ccc bootstrap-system'..."
    info ""

    # exec ersetzt firstboot.sh-Process durch ccc bootstrap-system.
    # Args + ENV-Vars (TZ, LOCALES, DEFAULT_LOCALE, PKGS, REMOVE_DESELECTED,
    # DIST_UPGRADE, XED_LANG) werden durchgereicht. PATH wird vorab gesetzt
    # damit ccc selbst gefunden wird (Hand-off ist VOR Re-Login).
    export PATH="${PIPX_BIN_DIR_PATH}:${PATH:-/usr/sbin:/usr/bin:/sbin:/bin}"
    exec "$CCC_BIN_LINK" bootstrap-system "$@"
}

# === Main ===

main() {
    banner
    require_root
    init_log_file
    require_supported_distro
    bootstrap_apt
    install_cc_suite
    setup_path_fix
    hand_off_to_ccc "$@"
}

main "$@"
