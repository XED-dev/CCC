#!/bin/bash
# firstboot.sh v0.9.1 — cBOX@ /Container Control Bash-Schmal-Bootstrap
#
# Quelle:    https://github.com/XED-dev/CCC
# Aufruf:    bash <(curl -s https://ccc.xed.dev/firstboot.sh)
# Lokal:     bash firstboot.sh
#
# Was es tut (~200 Zeilen statt 1198 in v0.8.4):
#   Phase 0   — Pre-Flight (root + distro + Audit-Log-Init)
#   Phase 1   — apt install python3-Stack + pipx + Bootstrap-Pakete
#   Phase 2   — pipx install xed-ccc + xed-cca mit Version-Pin (PyPI-API)
#   Phase 2.5 — Version-Verify mit User-Agency (Edge-Case-Recovery)
#   Phase 3   — PATH-Fix (/etc/profile.d + /etc/bash.bashrc, pct-enter-Falle)
#   Phase 4   — exec /usr/local/bin/ccc bootstrap-system "$@"
#
# Phasen 2-7 von v0.8.4 (TZ/Locales/Pakete/Editor/Dist-Upgrade/Confirm) wandern
# in das ccc-Python-Verb 'bootstrap-system'. ENV-Vars (TZ, LOCALES, ...) werden
# via exec durchgereicht. Whiptail-State-Machine + i18n laufen in Python.
#
# Lizenz: MIT (siehe LICENSE im XED-dev/CCC-Repo)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# === Globals ===

VERSION="0.9.1"
SCRIPT_NAME="firstboot.sh"
FIRSTBOOT_LOG_FILE="/var/log/xed-firstboot.log"

# pipx-System-Setup (env-vars statt --global wegen pipx 1.4.x kompat —
# Pattern: reference_pipx_for_cli_tools.md, AI036 2026-05-04)
PIPX_HOME_DIR="/opt/pipx"
PIPX_BIN_DIR_PATH="/usr/local/bin"

CCC_BIN_LINK="/usr/local/bin/ccc"
CCA_BIN_LINK="/usr/local/bin/cca"

# v0.9.1: User-Agency-Box Max-Retries-Cap (verify_version_with_user_agency).
VERIFY_MAX_RETRIES=5

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

# === PHASE/VERIFY-Marker fuer Run-Differenz-Diagnose ===
# Format identisch zu Python-Lib ccc.system.audit_log
# (phase_start/phase_end/verify): ein 'grep "\[PHASE\]" /var/log/xed-firstboot.log'
# liest Bash- und Python-Marker auf derselben Datei.
phase_start() {
    local name="$1"; shift
    local ctx=""
    [ $# -gt 0 ] && ctx=" ($*)"
    log_to_file "PHASE" "${name} start${ctx}"
}

phase_end() {
    local name="$1"
    local rc="${2:-0}"
    shift 2 || shift $#
    local extra=""
    [ $# -gt 0 ] && extra=", $*"
    log_to_file "PHASE" "${name} end (rc=${rc}${extra})"
}

verify() {
    local key="$1"
    local value="$2"
    log_to_file "VERIFY" "${key}=${value}"
}

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
    phase_start "firstboot.sh:Phase-1-apt-install"
    info "apt update + Python-Stack + pipx + Bootstrap-Pakete installieren..."
    apt-get update -qq </dev/null
    apt-get install -y -qq --no-install-recommends \
        python3 python3-venv git pipx \
        whiptail locales tzdata ca-certificates </dev/null

    if ! command -v pipx >/dev/null 2>&1; then
        err "pipx nicht verfuegbar nach Install — Bootstrap fehlgeschlagen."
        phase_end "firstboot.sh:Phase-1-apt-install" 1
        exit 1
    fi
    verify "pipx-version" "$(pipx --version 2>&1 | head -1)"
    ok "Python-Stack bereit: pipx $(pipx --version 2>&1 | head -1)"
    phase_end "firstboot.sh:Phase-1-apt-install" 0
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

# === Phase 2 helpers — Version-Quellen (param-driven für ccc + cca) ===

# Bootstrap-Distribution-Pattern: Initial-Install mit Version-Pin via
# PyPI-API-Query. Pin umgeht pipx < 1.3.0 fehlendes automatic
# --force-reinstall-Forwarding (Ubuntu 22.04 Default ist pipx 1.0.0).
# Quelle: pipx CHANGELOG (https://pipx.pypa.io/stable/changelog/) —
# „pipx 1.3.0 (Feb 2024): Force now implies --force-reinstall to pip".
# Stdlib-Reflex: python3 ist nach Phase-1-apt verfuegbar.
# Pattern aus cci v0.0.6 — Memory: reference_pipx_force_version_pin.md.

_pipx_installed_version() {
    local pkg="$1"
    pipx list --json 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['venvs']['$pkg']['metadata']['main_package']['package_version'])
except (KeyError, json.JSONDecodeError):
    pass
" 2>/dev/null
}

_pypi_latest_version() {
    local pkg="$1"
    curl -sSf --max-time 10 \
        -H "User-Agent: xed-ccc-firstboot/${VERSION}" \
        "https://pypi.org/pypi/${pkg}/json" 2>/dev/null | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin)['info']['version'])
except (KeyError, json.JSONDecodeError):
    pass
" 2>/dev/null
}

# install_one_package: param-driven install mit Version-Pin + Fallback
# bei PyPI-API-Fail + Verify-Marker + User-Agency-Aufruf. Per-Paket-
# Aufruf für ccc + cca (saubere Edge-Case-Trennung).

install_one_package() {
    local pkg="$1"
    local latest
    latest=$(_pypi_latest_version "$pkg")
    if [ -n "$latest" ]; then
        info "${pkg} via pipx install --force ${pkg}==${latest}..."
        pipx install --force "${pkg}==${latest}" --pip-args="--no-cache-dir"
    else
        info "${pkg} via pipx install --force (PyPI-Check failed, Fallback ohne Pin)..."
        pipx install --force "$pkg" --pip-args="--no-cache-dir"
    fi
    ok "${pkg} installiert via pipx"

    # Direkter Wheel-Pfad-Aufruf umgeht PATH-Cache + Symlink-Drift —
    # zeigt tatsaechlich installierte Version (Run-Differenz-Diagnose).
    local tool_name="${pkg#xed-}"  # xed-ccc -> ccc, xed-cca -> cca
    verify "${pkg}-installed-version" "$(/opt/pipx/venvs/"${pkg}"/bin/"${tool_name}" --version 2>/dev/null | awk '{print $NF}')"

    # SS7-Adaption: User-Agency-Box bei Edge-Cases (PyPI-API down, oder
    # PyPI-Drift zwischen Install und Verify). System luegt nicht statt
    # Cache-Hide-Magie.
    verify_version_with_user_agency "$pkg"
}

install_cc_suite() {
    phase_start "firstboot.sh:Phase-2-pipx-install"
    export PIPX_HOME="$PIPX_HOME_DIR"
    export PIPX_BIN_DIR="$PIPX_BIN_DIR_PATH"

    migrate_old_symlink "$CCC_BIN_LINK"
    migrate_old_symlink "$CCA_BIN_LINK"

    install_one_package "xed-ccc"
    install_one_package "xed-cca"

    ok "CC-Suite bereit: ccc + cca via pipx"
    phase_end "firstboot.sh:Phase-2-pipx-install" 0
}

# === Phase 2.5 — Version-Verify mit User-Agency (SS7-Adaption aus cci v0.0.6) ===

# Pattern-Anker: „System luegt nicht statt Cache-Hide-Magie."
# Default ist IMMER Update auf PyPI-latest (User-Intent von `bash <(curl)`).
# [k] erlaubt User explizit „bei installierter bleiben". [n] abbrechen.
# Max-Retries-Cap gegen Infinite-Loop. Defense-Recovery bei Check-Failure.

verify_version_with_user_agency() {
    local pkg="$1"
    local retry_count=0
    while true; do
        local installed latest
        installed=$(_pipx_installed_version "$pkg")
        latest=$(_pypi_latest_version "$pkg")

        # Defense-Recovery: bei Check-Failure einfach weiter (kein Block).
        if [ -z "$installed" ]; then
            warn "${pkg}: Installed-Version-Check failed — weiter ohne Verify."
            return 0
        fi
        if [ -z "$latest" ]; then
            warn "${pkg}: PyPI-Check failed (Netzwerk/Timeout) — weiter mit installed v${installed}."
            return 0
        fi

        # Match — OK.
        if [ "$installed" = "$latest" ]; then
            ok "${pkg} Version-Match: v${installed} (installed = PyPI latest)"
            return 0
        fi

        # Max-Retries erreicht — Resignation mit Warning (System luegt nicht).
        if [ "$retry_count" -ge "$VERIFY_MAX_RETRIES" ]; then
            warn "${pkg} Max-Retries (${VERIFY_MAX_RETRIES}) erreicht — installed v${installed} bleibt (PyPI latest waere v${latest})."
            return 0
        fi

        # Versions-Divergenz — User-Agency mit Default=Update.
        echo
        echo "  ┌─ Versions-Divergenz ──────────────────────────────────────┐"
        printf "  │ Paket: %-51s│\n" "${pkg}"
        printf "  │ Installiert: v%-44s│\n" "${installed}"
        printf "  │ PyPI latest: v%-44s│\n" "${latest}"
        echo "  │ Ursache: pipx < 1.3.0 fehlt automatic --force-reinstall.  │"
        echo "  └───────────────────────────────────────────────────────────┘"
        echo
        echo "  [Y] Auf v${latest} updaten  (Default — empfohlen)"
        echo "  [k] Bei v${installed} bleiben"
        echo "  [n] Abbrechen"
        echo
        local response=""
        read -r -p "  Auswahl [Y/k/n]: " response
        case "${response:-Y}" in
            [Kk])
                ok "${pkg} User-Wahl [k]: bei v${installed} bleiben."
                return 0
                ;;
            [Nn])
                err "${pkg} User-Wahl [n]: Abbrechen."
                exit 1
                ;;
            *)
                # Default + unklare Auswahl → Update (User-Intent-konform).
                retry_count=$((retry_count + 1))
                info "${pkg} Update ${retry_count}/${VERIFY_MAX_RETRIES}: pipx install --force ${pkg}==${latest}..."
                pipx install --force "${pkg}==${latest}" --pip-args="--no-cache-dir"
                ;;
        esac
    done
}

# === Phase 3 — PATH-Fix (pct-enter-Falle) ===

# pct enter startet NON-LOGIN interactive bash mit minimal-PATH
# (/sbin:/bin:/usr/sbin:/usr/bin) ohne /usr/local/bin. Daher braucht
# /etc/bash.bashrc den PATH-Fix. /etc/profile.d/ zusaetzlich fuer Login-Shells.
# Pattern: reference_path_fix_shell_modes.md (AI035, 2026-05-03).
setup_path_fix() {
    phase_start "firstboot.sh:Phase-3-path-fix"
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
    phase_end "firstboot.sh:Phase-3-path-fix" 0
}

# === Phase 4 — Hand-off zu ccc bootstrap-system ===

hand_off_to_ccc() {
    # KEIN phase_end auf success-Pfad — exec ersetzt Prozess. Hand-off-
    # Boundary wird durch das nachfolgende '[PHASE] ccc:bootstrap-system
    # start' im Python-Verb gesetzt (SS6.3-Pendant in bootstrap_system.py).
    phase_start "firstboot.sh:Phase-4-hand-off"
    if ! "$CCC_BIN_LINK" --version >/dev/null 2>&1; then
        err "ccc nicht aufrufbar: $CCC_BIN_LINK"
        err "  pipx list — Diagnose noetig"
        phase_end "firstboot.sh:Phase-4-hand-off" 1
        exit 1
    fi

    # Ground-truth-Verifikation: was wird gleich exec't? Vergleich zu
    # Phase-2 verify gibt zweiten Diagnose-Punkt fuer Symlink/PATH-Drift
    # zwischen pipx-install und exec.
    verify "ccc-cli-version" "$($CCC_BIN_LINK --version 2>&1 | awk '{print $NF}')"
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
