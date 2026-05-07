# Changelog

Alle bemerkenswerten Änderungen an `xed-ccc` werden hier dokumentiert.

Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.2] — 2026-05-07

### Behoben (Bug-Fix — Ubuntu 24.04 Phased-Updates)

- **`apply_dist_upgrade()` skippte phased Pakete still** — Ubuntu 24.04+
  rollt Updates wellenweise (Phased-Update-Percentage). Default-Verhalten
  von `apt-get dist-upgrade -y -qq` defernt phased Pakete ohne Diagnose-
  Output: User klickte Whiptail-`<Yes>`, Phase-Marker zeigte `rc=0`, aber
  keine Pakete wurden installiert.

  Fix in `phases/apt.py::apply_dist_upgrade()`: explizit
  `-o APT::Get::Always-Include-Phased-Updates=true` Flag setzen.

  Verifikation auf 5521-pmDESK 2026-05-07: ohne Flag wurden 9 deferred
  phased Pakete (gnome-shell-Stack + libheif-Stack) skipped, mit Flag
  installiert. apt's eigene Diagnose-Ausgabe ist die kanonische Quelle:

      The following upgrades have been deferred due to phasing:
        gnome-shell gnome-shell-common ... libheif1
      0 aktualisiert, 0 neu installiert, ... 9 nicht aktualisiert.

  Bug ist latent seit firstboot.sh v0.8.4 (Z831 hatte identischen Pattern
  ohne Flag), manifestiert sich abhängig von Ubuntu's Phasing-Schedule
  pro Test-Box-Zeitpunkt. Selbstheil-Workflow blieb funktional bis die
  Audit-Log-Marker (SS6.1-3) den silent-no-op sichtbar machten.

### Tests

- `test_apply_dist_upgrade_with_dist_upgrade_flag` aktualisiert: Assertion
  prüft jetzt Flag-Präsenz statt strict-prefix-Match. 63/63 grün.

[0.2.2]: https://github.com/XED-dev/CCC/releases/tag/v0.2.2

## [0.2.1] — 2026-05-07

### Geändert (Pattern-Switch zurück zu v0.8.4-Style)

- **`firstboot.sh::install_cc_suite()`** zurück zum AI036 v0.8.4-Pattern
  (`if pipx list ... then pipx upgrade else pipx install`) PLUS
  `--pip-args="--no-cache-dir"`-Flag.
  Senior-Schärfung 2026-05-06 zu `pipx install --force` ist damit
  zurückgenommen — `pipx upgrade` ist semantisch sauberer („falls neuere
  Version, zieh sie") als `pipx install --force` („immer reinstallieren").
  Code-Switch ist akzeptabel, war aber **nicht der Bug-Fix den die v0.2.1-
  Releasenotes zunächst behauptet hatten** (siehe Korrektur unten).

### Korrektur 2026-05-07 — Wurzel-Analyse war faktisch falsch

Initial-Releasenotes von v0.2.1 (am gleichen Tag, später korrigiert):
hatten den „Re-Run-Window beim `bash <(curl)`"-Bug auf einen
**pip-HTTP-Cache-Side-Effect** (`~/.cache/pip/http/` TTL ~10 Min)
zurückgeführt. Diese These widerspricht der empirischen Beobachtung
auf 5521-pmDESK 2026-05-07 (SS6.5-Live-Test): auch nach v0.2.1-Release
mit `--no-cache-dir`-Flag trat das Re-Run-Window weiter auf, wartezeit-
unabhängig (5 Min wie 20 Min identisch).

**Echte Wurzel** (Web-Search nach DevOps-Direktive: zuerst Community
fragen, nicht Code spekulativ ändern): **PyPI-Fastly-CDN-Stale-Backend-
Pattern.** PyPI nutzt Fastly mit mehreren Backend-Servern, deren Cache
asynchron + unabhängig invalidiert. DNS-Round-Robin verteilt Requests
an `pypi.org`-IPs an Backends mit unterschiedlichem Cache-Stand. Run 1
trifft mit gewisser Wahrscheinlichkeit ein stale-Backend, Run 2 ein
fresh-Backend — wartezeit-unabhängig, weil Backends nicht zeit-gebunden
invalidieren. Quelle: Plone-Community-Diskussion 2018, warehouse-Issue
\#11949.

**Konsequenz:** der Bug ist **client-side nicht fixbar**. `--no-cache-dir`
hilft nicht (bypasst nur lokalen pip-Cache, nicht Server-side CDN).
Der Pattern-Switch zu `pipx upgrade` ist trotzdem sauberer Code, aber
nicht der versprochene Workaround. Folge-Plan SS7: transparente Version-
Auswahl-UX in `bootstrap-system` (User klickt „Suche neue Version" so
oft bis erwartete Version sichtbar — Cache-Realität wird sichtbar
gemacht statt versteckt).

Memory-Anker: `feedback_investigations_hierarchy.md` (Senior-Direktive
„WebSearch zuerst, Code-Iterationen zuletzt") + `reference_pypi_initial_
upload_token_scope.md` Anhang 2026-05-07 (PyPI-Fastly-CDN-Pattern).

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
