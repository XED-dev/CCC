# Changelog

Alle bemerkenswerten Änderungen an `xed-ccc` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.0.2] — 2026-05-04

### Geändert

- **Branding aktualisiert** — `cBUZZ Container Control` →
  `cBOX@ /Container Control`. Konsistente Brand-Identität für
  cBOX.at/YOU by XED.dev Tools via Collective Context (CC).
- `pyproject.toml` description + Typer-CLI-Help + README.md + Pages-Landing
  (`docs/index.html`: Title + h1 + Footer) konsistent gebrandet.
- keyword in `pyproject.toml`: `cbuzz` → `cbox`.

### Architektur

Keine Code-Logic-Änderung — reines Brand-Update als Patch-Bump.

[0.0.2]: https://github.com/XED-dev/CCC/releases/tag/v0.0.2

## [0.0.1] — 2026-05-03

### Hinzugefügt

- **PyPI-Skelett** (Name-Reservierung auf <https://pypi.org/project/xed-ccc/>)
- **CLI-Skelett** mit drei Top-Level-Commands (analog `pct`):
  - `ccc list` — zeigt verfügbare Rollen mit Status (bereit/Stub)
  - `ccc create <role> [--dry-run]` — installiert eine Rolle (heute nur Plan)
  - `ccc menu` — TUI-Stub (Textual-Implementation kommt später)
- **Rollen-Registry** in `src/ccc/roles/`:
  - `pmDESK` (Debian/Ubuntu Gnome-Desktop) — Stub mit Plan-Output
  - Geplant: `lxcHOST`, `osNGINX`, `commBOX`
- **firstboot.sh-Integration**: Phase 7 in `firstboot.sh` v0.7.0 installiert
  ccc direkt (apt python3-Stack + git clone /opt/xed-ccc/ + venv + symlink
  `/usr/local/bin/ccc`). Self-contained, kein Sub-Aufruf eines weiteren
  Bash-Skripts mehr.
- **Distribution doppelt**: PyPI (`pipx install xed-ccc`) + automatisch
  via `firstboot.sh` Phase 7 (für frische LXC-Boxen)

### Architektur-Hinweise

- Python ≥ 3.11, hatchling-Build-Backend, Typer + Rich als Dependencies
- `pyproject.toml` mit dynamischer Versionierung aus `src/ccc/_version.py`
- Optional-Dependencies: `tui` (Textual), `dev` (pytest)

[0.0.1]: https://github.com/XED-dev/CCC/releases/tag/v0.0.1
