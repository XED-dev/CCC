"""pmDESK-Rolle: Debian/Ubuntu Gnome-Desktop für LXC-Boxen.

Stub-Implementation — Plan zeigt geplante Schritte, Apply ist noch nicht
implementiert. Kommt mit dem ersten echten Apply-Sprint.

Geplante Schritte (zu verifizieren in Live-Probe):
1. Erkennen Debian vs. Ubuntu
2. Installiere Desktop-Stack:
   - Debian:  task-gnome-desktop  (via tasksel) oder gnome-core
   - Ubuntu:  ubuntu-desktop-minimal
3. Installiere xrdp + dbus-x11 für Remote-Desktop-Zugang
4. Konfiguriere xrdp-Listen auf 0.0.0.0:3389
5. Erstelle non-root SysOps-User mit sudo-Privileg + RDP-Group
6. Optional: Wayland-Socket-Bind-Mount für Performance-GUI vom Host
   (siehe MEMORY reference_curl_bash_process_substitution.md)
"""

from __future__ import annotations

from rich.console import Console

from ccc.roles.base import Role

console = Console()


class PmDeskRole(Role):
    """pmDESK — Debian/Ubuntu Gnome Desktop in LXC-Box."""

    description = "Debian/Ubuntu Gnome Desktop (xrdp + Gnome-Stack)"
    is_implemented = False

    def plan(self) -> None:
        """Zeigt die geplanten Schritte."""
        steps = [
            ("1.", "Distro-Erkennung (lsb_release / os-release)"),
            ("2.", "Desktop-Stack installieren (task-gnome-desktop / ubuntu-desktop-minimal)"),
            ("3.", "xrdp + dbus-x11 + xorgxrdp installieren"),
            ("4.", "xrdp-Konfiguration: listen auf 0.0.0.0:3389"),
            ("5.", "SysOps-User anlegen (sudo + tsusers + ssl-cert)"),
            ("6.", "Optional: Wayland-Socket-Bind-Mount-Stub (für Phase 2)"),
        ]
        console.print("[bold]Geplante Schritte:[/bold]")
        for num, desc in steps:
            console.print(f"  {num} {desc}")

    def apply(self) -> None:
        """Führt die Konfiguration aus — noch nicht implementiert."""
        raise NotImplementedError(
            "pmDESK.apply() ist noch ein Stub. "
            "Implementation kommt mit dem ersten Apply-Sprint."
        )
