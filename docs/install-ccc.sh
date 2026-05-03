#!/bin/bash
# install-ccc.sh — Curl-Bash-Bootstrap für xed-ccc Python-Tool
#
# Quelle:    https://github.com/XED-dev/CCC
# Aufruf:    bash <(curl -s https://ccc.xed.dev/install-ccc.sh)
# Voraussetzung: firstboot.sh durchgelaufen (python3 + venv installiert)
#
# Was es tut:
#   1. Pre-Flight: python3 + python3-venv vorhanden? Sonst apt install
#   2. Repo klonen nach /opt/xed-ccc/ (oder Update wenn schon da)
#   3. venv erstellen + Tool installieren (pip install -e .)
#   4. Symlink /usr/local/bin/ccc → /opt/xed-ccc/.venv/bin/ccc
#   5. Smoke-Test: ccc --version
#
# Idempotenz: kann beliebig oft aufgerufen werden, konvergiert.
#
# Lizenz: MIT (siehe LICENSE im XED-dev/CCC-Repo)

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

VERSION="0.0.1"
REPO_URL="https://github.com/XED-dev/CCC.git"
INSTALL_DIR="/opt/xed-ccc"
VENV_DIR="${INSTALL_DIR}/.venv"
BIN_LINK="/usr/local/bin/ccc"

err()  { echo "ERROR: $*" >&2; }
info() { echo "→ $*"; }
ok()   { echo "✔ $*"; }

banner() {
    echo
    echo "========================================================================"
    echo "  XED-CCC install-ccc.sh v${VERSION}"
    echo "  Bootstrap des Python-Tools für nested LXC-Stacks"
    echo "========================================================================"
    echo
}

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        err "Dieses Skript muss als root laufen."
        err "  Tipp: sudo bash <(curl -s https://ccc.xed.dev/install-ccc.sh)"
        exit 1
    fi
}

install_python_deps() {
    info "Pre-Flight: python3 + python3-venv + git..."
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=("python3")
    command -v git >/dev/null 2>&1 || missing+=("git")
    # python3-venv-Check via dpkg (kein direkter Binary)
    dpkg -l python3-venv 2>/dev/null | grep -q "^ii" || missing+=("python3-venv")

    if [ ${#missing[@]} -gt 0 ]; then
        info "Fehlende Pakete installieren: ${missing[*]}"
        apt-get update -qq </dev/null
        apt-get install -y -qq --no-install-recommends "${missing[@]}" </dev/null
    fi
    ok "Python-Stack bereit: $(python3 --version)"
}

clone_or_update_repo() {
    if [ -d "${INSTALL_DIR}/.git" ]; then
        info "Repo existiert — Update via fetch + reset --hard..."
        git -C "$INSTALL_DIR" fetch --quiet origin main
        git -C "$INSTALL_DIR" reset --hard --quiet origin/main
    else
        info "Repo nach ${INSTALL_DIR} klonen..."
        # Falls Verzeichnis existiert aber kein Repo: backup-mv (no-rm-Regel)
        if [ -d "$INSTALL_DIR" ]; then
            local ts
            ts=$(date +%Y%m%d-%H%M%S)
            mv "$INSTALL_DIR" "${INSTALL_DIR}.replaced.${ts}"
            info "Bestehendes Verzeichnis gesichert nach ${INSTALL_DIR}.replaced.${ts}"
        fi
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --quiet --depth 1 "$REPO_URL" "$INSTALL_DIR"
    fi
    ok "Repo bereit: $(git -C "$INSTALL_DIR" rev-parse --short HEAD)"
}

setup_venv() {
    if [ -x "${VENV_DIR}/bin/python3" ]; then
        info "venv existiert — Update..."
    else
        info "venv erstellen in ${VENV_DIR}..."
        python3 -m venv "$VENV_DIR"
    fi
    info "pip + xed-ccc installieren (editable-mode)..."
    "${VENV_DIR}/bin/pip" install --quiet --upgrade pip </dev/null
    "${VENV_DIR}/bin/pip" install --quiet -e "$INSTALL_DIR" </dev/null
    ok "Tool installiert: $(${VENV_DIR}/bin/ccc --version 2>&1 | head -1)"
}

setup_symlink() {
    info "Symlink ${BIN_LINK} → ${VENV_DIR}/bin/ccc..."
    ln -sf "${VENV_DIR}/bin/ccc" "$BIN_LINK"
    ok "Symlink aktiv. Aufruf: ccc --help"
}

smoke_test() {
    info "Smoke-Test: ccc --version"
    if "$BIN_LINK" --version; then
        ok "Smoke-Test grün."
    else
        err "Smoke-Test fehlgeschlagen — ccc --version returned non-zero."
        exit 1
    fi
}

main() {
    banner
    require_root
    install_python_deps
    clone_or_update_repo
    setup_venv
    setup_symlink
    smoke_test

    echo
    echo "------------------------------------------------------------"
    echo "  XED-CCC bereit. Nächste Schritte:"
    echo "     ccc --help           # alle Verben"
    echo "     ccc list             # verfügbare Rollen"
    echo "     ccc create pmDESK    # Beispiel: Gnome-Desktop installieren"
    echo "------------------------------------------------------------"
}

main "$@"
