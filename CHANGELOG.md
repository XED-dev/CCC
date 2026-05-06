# Changelog

Alle bemerkenswerten Änderungen an `xed-ccc` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.1] — 2026-05-07

### Behoben (Bug-Fix)

- **Re-Release-Window beim `bash <(curl)`-Selbstheil-Workflow** —
  `firstboot.sh::install_cc_suite()` verwendet wieder den AI036 v0.8.4-
  Pattern (`if pipx list ... then pipx upgrade else pipx install`) PLUS
  `--pip-args="--no-cache-dir"` als doppelten Cache-Bypass.

  Wurzel des Bugs (durch SS6-Marker im Audit-Log diagnostiziert):
  Senior-Schärfung 2026-05-06 zu `pipx install --force xed-ccc` (ohne
  Cache-Bypass) hat den pip-HTTP-Cache-Side-Effect (`~/.cache/pip/http/`
  TTL ~10 Min) wieder aktiviert. Folge: bei kurz aufeinanderfolgenden
  PyPI-Releases zog Run 1 unmittelbar nach Upload noch die alte Version,
  Run 2 nach ~12 Min die neue (ursprüngliche AI040-Onboarding §Bug-
  Beobachtung 2026-05-06).

  AI036's v0.8.4-Pattern hatte dieses Verhalten nicht (DevOps-Erinnerung:
  „lief zuverlässig in wenigen Minuten") — `pipx upgrade` triggert
  `pip install --upgrade`-Resolver mit anderem Cache-Pfad-Verhalten,
  plus jetzt `--no-cache-dir` als deterministischer Bypass.

  Audit-Log [VERIFY]-Marker (SS6.1-3) bleiben als Forensik-Trail aktiv
  für künftige Diagnose-Cycles. Beweis des Selbstheil-Workflow-Pfades
  (`bash <(curl)` → SOFORT-v0.2.1 ohne Re-Run-Wait) erfolgt im SS6.5-
  Live-Test auf 5521-pmDESK nach diesem Release.

[0.2.1]: https://github.com/XED-dev/CCC/releases/tag/v0.2.1

## [0.2.0] — 2026-05-07

### Hinzugefügt (Audit-Log-Schema-Erweiterung)

- **`[PHASE]` und `[VERIFY]` Marker im Audit-Log** — drei Module-Funktionen
  in `ccc.system.audit_log` (`phase_start`, `phase_end`, `verify`) plus
  Context-Manager `phase` zur Boilerplate-Reduktion (try/except + rc=0/1
  + re-raise gekapselt). Format Bash↔Python identisch:
  `<ISO-UTC> [PHASE] <name> start (k=v, ...)` / `[VERIFY] <key>=<value>`.
  Ein `grep '\[PHASE\]' /var/log/xed-firstboot.log` liefert lückenlosen
  Run-Forensik-Trail von Bash- bis Python-Layer.
- **firstboot.sh Bash-Spiegel-Helper** — `phase_start` / `phase_end` /
  `verify` als Bash-Funktionen via `log_to_file`. Phase 1-4 mit Markern
  + drei Diagnose-Verify-Checkpoints für pipx-Run-Differenz-Diagnose:
  `pipx-version` (pipx selbst) + `xed-ccc-installed-version` (via Wheel-
  Pfad direkt) + `ccc-cli-version` (via Symlink, Ground-truth vor exec).
- **bootstrap_system.py Composition-Marker** — Outer-Boundary
  `with phase("ccc:bootstrap-system")` plus 7 Inner-Marker um Phase-
  Aufrufe (self-heal-dpkg, self-heal-pro-notice, apply-timezone,
  apply-locales, apply-packages, apply-dist-upgrade, apply-editor).
  ctx-kwargs als minimal-Diagnose-Daten (tz, count).

### Geändert

- **Audit-Log-Format-Drift bei Verb-Boundary:** `log.info("bootstrap-system
  start/done")` ersetzt durch Outer-Phase-Marker
  (`<ISO> [INFO] [PHASE] ccc:bootstrap-system start` / `... end (rc=0)`).
  Additive-kompatibel mit v0.1.x-Logs (alter String erscheint nicht mehr,
  aber Log-Pfad + Format-Familie identisch — kein Parser-Bruch erwartet).

### Tests

- 63 pytest-Cases (CCC) grün — 6 neue Cases (4 für `phase_start`/
  `phase_end`/`verify` in SS6.1, 2 für Context-Manager in SS6.3),
  kompatibel mit bestehender `cleanup_loggers`-autouse-Fixture.

### Lehrziel + Begründung Minor-Bump

Aufgabe: Run-1-vs-Run-2-pipx-Verhalten auf 5521-pmDESK aus Audit-Log-
Markern selbst diagnostizierbar machen statt Live-Forensik. Senior-AI037-
Direktive: Audit-Log-Schema-Erweiterung ist additive Capability (additiv-
kompatibel mit v0.1.x-Logs), substantiell genug für Minor-Bump statt Patch.

[0.2.0]: https://github.com/XED-dev/CCC/releases/tag/v0.2.0

## [0.1.1] — 2026-05-06

### Hinzugefügt (UX-Patch)

- **Hint-Block am Ende von `ccc bootstrap-system`** — Audit-Log-Pfad +
  4 grep/tail/less-Beispiele + Verb-Übersicht (`ccc list`, `cca list`,
  `cca install <app>`). Wartungs-Pfad sichtbar machen — Logs sind A+O
  des Developer-Lebens (AI036-Direktive 2026-05-04).

### Bug-Fix-Lehre

Beim v0.1.0-Refactor (Bash-Schmal/Python-Breit) wurde der AI036-Hint-Block
aus `firstboot.sh` v0.8.4 (Z1186-1194) ersatzlos gestrichen + nicht in
das Python-Verb portiert. SS5-Live-Test 2026-05-06 auf 5521-pmDESK hat
das Issue gefangen — DevOps hat angemerkt dass der Audit-Log-Pfad-Hinweis
am Ende fehlt. v0.1.1 zieht den Block ins Python-Verb nach.

Pattern-Anker für Senior-Sweep-Repertoire: bei Bash→Python-Migration nicht
nur Code-Verhalten, sondern auch UX-Output-Treue prüfen (End-of-Run-Output
+ Hint-Blöcke + Wartungs-Pfade).

[0.1.1]: https://github.com/XED-dev/CCC/releases/tag/v0.1.1

## [0.1.0] — 2026-05-06

### Geändert (Major Refactor — Bash-Schmal/Python-Breit)

- **firstboot.sh-Reduktion 1198 → ~190 Zeilen.** Phasen 2-7 von v0.8.4
  (TZ/Locales/Pakete/Editor/Dist-Upgrade/Confirm) wandern in das neue
  Python-Verb `ccc bootstrap-system`. Bash bleibt nur für: Pre-Flight
  (root + distro) + apt install python3-Stack + pipx install CC-Suite +
  PATH-Fix + exec ccc bootstrap-system. Archiv-Snapshot
  `firstboot-v0.8.4.sh.archive` no-deletion-konform im scripts/.

### Hinzugefügt

- **Self-Heal-Lib** in `ccc/system/self_heal/`:
  - `safe_purge` — apt-get purge mit Cascade-Schutz via `--simulate`-Parsing
    + Whitelist (verhindert Cascade-Vorfall mit destruktivem Pro-Client-Purge)
  - `pro_notice` — non-destruktive Ubuntu-Pro-Werbung-Deaktivierung (pro CLI
    + ESM-Hook-mv .bak + systemctl disable apt-news.service)
  - `dpkg` Composite — snap-purge + dpkg --configure -a + apt install -f +
    apt autoremove --purge mit DEBIAN_FRONTEND=noninteractive env
- **System-Lib** in `ccc/system/`:
  - `audit_log` — RotatingFileHandler mit ISO-UTC-Format kompatibel zu Bash
  - `marker` — FIRSTBOOT_MARKER Idempotenz-Helper
  - `pkg` — dpkg-query + locale-status (drei-wertig: ACTIVE/DISABLED/ABSENT)
    + Whiptail-Pre-Select-Helper mit first-run-Default-Fallback
  - `whiptail` — subprocess-Wrapper für TTY-Hybrid-Dialoge
    (msgbox/yesno/menu/checklist)
  - `i18n` — DE/EN-Strings-Dict (~55 Keys × 2 Sprachen) mit drei-stufigem
    Fallback (lang → DEFAULT_LANG → `<missing:key>`-marker)
- **Phase-Funktionen** in `ccc/commands/phases/`:
  - `locale.py`: `apply_timezone` + `apply_locales` mit Diff-Logik enable/disable
  - `apt.py`: `apply_packages` + `apply_dist_upgrade` mit Multi-Mode
    (interactive/ENV-Override) + Remove-Confirmation
  - `editor.py`: `apply_editor` (EDITOR=nano in /etc/environment, idempotent)
- **Verb `ccc bootstrap-system`** mit Whiptail-State-Machine (6 Phasen mit
  Back-Button + Re-Prompt-bei-leerer-Auswahl + Phase-1-Abort-Confirm +
  Phase-6-Confirm-No-Back-zu-5). Eingabe-Strategie: Typer-Args mit envvar=
  oder TTY-Whiptail oder Skript-Defaults.

### Tests

- 57 pytest-Cases (CCC) grün — alle Lib-Module + alle Phase-Funktionen +
  Verb-Composition + State-Machine-Pfade gemockt-getestet.

### Architektur-Notiz

CC-Suite-Pattern in Stein: firstboot.sh = Bash-Schmal-Bootstrap, ccc/cca =
Python-Werkzeuge. Plus Lib-Sharing zwischen ccc + cca via Cross-Repo-Imports
(z.B. `cca.apps.gnome` importiert `ccc.system.self_heal.self_heal_dpkg`).

[0.1.0]: https://github.com/XED-dev/CCC/releases/tag/v0.1.0

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
