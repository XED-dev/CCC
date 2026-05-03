# Changelog

Alle bemerkenswerten Änderungen an `xed-ccc` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

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
- **firstboot.sh-Bridge**: Phase 7 in `firstboot.sh` v0.6.0 ruft optional
  `bash <(curl -s https://ccc.xed.dev/install-ccc.sh)` für Python-Tool-Install
- **Distribution doppelt**: PyPI (`pip install xed-ccc`) + curl-Bash
  (`bash <(curl -s https://ccc.xed.dev/install-ccc.sh)`)

### Architektur-Hinweise

- Python ≥ 3.11, hatchling-Build-Backend, Typer + Rich als Dependencies
- `pyproject.toml` mit dynamischer Versionierung aus `src/ccc/_version.py`
- Optional-Dependencies: `tui` (Textual), `dev` (pytest)

[0.0.1]: https://github.com/XED-dev/CCC/releases/tag/v0.0.1
