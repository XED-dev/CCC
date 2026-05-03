"""xed-ccc — cBUZZ Container Control.

Python-Werkzeug für nested LXC-Stacks auf Proxmox VE 9 mit Debian/Ubuntu.
Pendant zu `pct` (Proxmox Container Toolkit) — vertraut wie pct, aber
mit Rollen-Profilen, TUI und API-Schnittstelle.

Architektur folgt dem Drei-Skripte-Modell aus dem WHITEPAPER:
1. firstboot.sh   — Bash-Basis-Setup (Locale/TZ/Pakete)
2. ccc            — dieses Tool, Rollen-Konfiguration
3. ccc-tui        — Textual-TUI als Pendant zum Proxmox-Webinterface (geplant)
"""

from ccc._version import __version__

__all__ = ["__version__"]
