# XED /CCC — cBUZZ Container Control

> **Bash-Bootstrap und Werkzeuge für nested LXC-Stacks** auf Proxmox VE 9 mit Debian 13 / Ubuntu 24.04+.
>
> Status: Stufe 1 — `firstboot.sh` (Basis-Setup für frische Boxen)
> Lizenz: MIT
> Distribution: <https://ccc.xed.dev>

---

## Schnellstart

In jeder frischen Debian/Ubuntu-LXC-Box als root:

```bash
bash <(curl -s https://ccc.xed.dev/firstboot.sh)
```

Das setzt **Zeitzone, Locales, Default-Editor und Basis-Pakete** — alles via Whiptail-TUI im Debian-Installer-Stil. Idempotent: kann beliebig oft wiederholt werden.

### Non-Interactive (CI / Auto-Provisioning)

```bash
TZ=UTC \
  LOCALES="de_AT.UTF-8 en_US.UTF-8" \
  DEFAULT_LOCALE=de_AT.UTF-8 \
  PKGS="htop curl wget sudo psmisc net-tools iproute2 iputils-ping gnupg nano" \
  bash <(curl -s https://ccc.xed.dev/firstboot.sh)
```

### TTY-Hinweis

`bash <(curl -s URL)` (Process Substitution) bewahrt das TTY und erlaubt
interaktive Whiptail-Dialoge. `curl URL | bash` (klassische Pipe) verbraucht
stdin und erzwingt Non-Interactive-Mode mit ENV-Defaults.

---

## Was `firstboot.sh` tut

| Phase | Inhalt |
|---|---|
| 0 | Pre-Flight (root-Check, Distro-Check, apt-Bootstrap, TTY-Detect) |
| 1 | Eingaben sammeln (Whiptail bei TTY, ENV-Vars sonst) |
| 2 | Zeitzone setzen (`/etc/timezone` + `/etc/localtime`) |
| 3 | Locales generieren + Default-Locale (`update-locale` → `/etc/default/locale`) |
| 4 | Basis-Pakete installieren (`--no-install-recommends`) |
| 5 | `EDITOR=nano` in `/etc/environment` (idempotent via grep-vor-write) |
| 6 | Abschluss-Banner |

**Bewusst nicht enthalten:** Bridge-/iptables-/nested-LXC-Setup. Das kommt
mit `lxc-host-setup.sh` (Skript 2/3, geplant) als separates Skript für
cBUZZ-Outer-Container.

---

## Roadmap

| Skript | Zweck | Status |
|---|---|---|
| `firstboot.sh` | Basis-Setup für jede frische Debian/Ubuntu-Box | **Stufe 1, live** |
| `lxc-host-setup.sh` | Outer-Container vorbereiten (Bridge, iptables, nested LXC) | geplant |
| `ccc-create.sh` | Inner-Container provisionieren (Bash v1) | geplant |
| `ccc` (Python) | CLI als Pendant zu `pct` (Typer + Pydantic) | geplant |
| `ccc-tui` (Python) | Textual-TUI als Pendant zum Proxmox-Webinterface | geplant |

Architektur und Designentscheidungen: siehe `WHITEPAPER.md` im
Entwicklungs-Workspace (privat).

---

## Designprinzipien

- **Vertrautheit > Eleganz** — `ccc` ≈ `pct` semantisch, `ccc-tui` ≈ Proxmox-Webinterface
- **Drei-Skripte-Modell** statt Universal-Skript mit Modus-Switch
- **Idempotenz** (mailinabox-Stil) — `curl ... | bash` jederzeit wiederholbar
- **Kaizen** — kleine Schritte, ausprobieren statt endlos planen
- **Bash für einmalige Setups, Python für wachsende Werkzeuge**

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).
