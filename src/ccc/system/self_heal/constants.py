"""Konstanten für ccc.system.self_heal — Whitelists und Paket-Listen.

Single source of truth für firstboot.sh + ccc-Rollen + cca-Apps.
Replicate aus firstboot.sh v0.8.4 CRITICAL_PACKAGES_WHITELIST +
SNAP_REDIRECT_PACKAGES_LIST.
"""

from __future__ import annotations

# Pakete, die niemals durch eine Cascade entfernt werden dürfen —
# würden Display-Stack oder Box-Identität zerstören. Wird in
# safe_purge() gegen die simulate-Cascade geprüft, Abort bei Treffer.
CRITICAL_PACKAGES_WHITELIST: tuple[str, ...] = (
    "vanilla-gnome-desktop",
    "gnome-core",
    "gnome-shell",
    "gnome-shell-common",
    "gnome-session",
    "gnome-terminal",
    "ubuntu-minimal",
    "xrdp",
    "xorgxrdp",
    "dbus-x11",
)

# Snap-Redirect-Pakete auf Ubuntu 22.04+ — bricht im LXC ohne snapd
# (Squashfs-mount, udev, cgroups). Pattern: reference_no_snap_in_lxc.md.
SNAP_REDIRECT_PACKAGES: tuple[str, ...] = (
    "firefox",
    "thunderbird",
    "chromium-browser",
    "gnome-software-plugin-snap",
    "snapd",
)
