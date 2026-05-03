"""xed-ccc CLI — Typer-basiertes Pendant zu pct.

Designprinzipien (siehe WHITEPAPER §2.3 + §8.1):
- Vertrautheit > Eleganz: Verben analog `pct` wo möglich
- Verb-Mapping: list, create, enter, status (analog pct)
- Eigene Subbefehlsräume nur wo nötig (`ccc role`, `ccc menu`)
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ccc._version import __version__
from ccc.roles import AVAILABLE_ROLES, get_role

app = typer.Typer(
    name="ccc",
    help="cBUZZ Container Control — Rollen-Konfiguration für LXC-Boxen.\n\n"
    "Nach `firstboot.sh` (Bash-Basis-Setup) kommt `ccc` als Python-Tool für\n"
    "Rollen-Konfiguration: pmDESK (Gnome-Desktop), lxcHOST (Firewall),\n"
    "osNGINX (Reverse-Proxy), commBOX (Communication-Stack) usw.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"xed-ccc [bold]v{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Zeige Version und beende.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """xed-ccc Top-Level-Callback. Lädt globale Optionen wie --version."""


@app.command("list")
def list_roles() -> None:
    """Listet verfügbare Rollen, die mit `ccc create <name>` installierbar sind.

    Beispiel:
        ccc list
    """
    table = Table(
        title="Verfügbare Rollen",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="bold")
    table.add_column("Beschreibung")
    table.add_column("Status", justify="center")

    for role_name, role_class in AVAILABLE_ROLES.items():
        instance = role_class()
        status = (
            "[green]bereit[/green]"
            if instance.is_implemented
            else "[yellow]Stub[/yellow]"
        )
        table.add_row(role_name, instance.description, status)

    console.print(table)
    console.print()
    console.print(
        "[dim]Hinweis: Stub-Rollen haben Skelett-Struktur, aber noch keine "
        "vollständige Implementation.[/dim]"
    )


@app.command("create")
def create_role(
    role: str = typer.Argument(
        ..., help="Rolle, die in der aktuellen Box installiert werden soll."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Zeige geplante Schritte, ohne sie auszuführen.",
    ),
) -> None:
    """Installiert eine Rolle in der aktuellen LXC-Box.

    Beispiel:
        ccc create pmDESK
        ccc create pmDESK --dry-run
    """
    role_class = get_role(role)
    if role_class is None:
        console.print(f"[red]Unbekannte Rolle:[/red] {role}")
        console.print(
            "Verfügbare Rollen: " + ", ".join(AVAILABLE_ROLES.keys())
        )
        raise typer.Exit(code=1)

    instance = role_class()
    console.print(
        f"[bold cyan]Installiere Rolle:[/bold cyan] {role} — {instance.description}"
    )

    if dry_run:
        console.print("[yellow]Dry-Run:[/yellow] keine Änderungen am System.")
        instance.plan()
    else:
        if not instance.is_implemented:
            console.print(
                f"[yellow]Hinweis:[/yellow] Rolle '{role}' ist noch ein Stub. "
                "Plan wird angezeigt; Apply ist noch nicht implementiert."
            )
            instance.plan()
            raise typer.Exit(code=2)
        instance.apply()
        console.print(f"[green]✔[/green] Rolle '{role}' installiert.")


@app.command("menu")
def menu() -> None:
    """Startet die interaktive TUI (Textual-basiert).

    Stub: noch nicht implementiert. Kommt mit dem ersten Textual-Sprint.

    Beispiel:
        ccc menu
    """
    console.print(
        "[yellow]TUI-Stub:[/yellow] `ccc menu` ist noch nicht implementiert.\n"
        "Geplant: Textual-App mit Rollen-Auswahl + Container-Status (analog\n"
        "Proxmox-Webinterface). Bis dahin: nutze `ccc list` + `ccc create <role>`."
    )
    raise typer.Exit(code=2)


def main() -> None:
    """Entry point für das `ccc`-Script (siehe pyproject.toml [project.scripts])."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[red]Abgebrochen.[/red]")
        sys.exit(130)


if __name__ == "__main__":
    main()
