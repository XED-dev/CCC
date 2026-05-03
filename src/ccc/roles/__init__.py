"""Rollen-Registry für xed-ccc.

Jede Rolle ist eine Klasse mit:
- description: Kurze Beschreibung der Rolle
- is_implemented: True wenn Apply-Logik vollständig
- plan(): zeigt geplante Schritte (Dry-Run)
- apply(): führt die Schritte aus

Rollen werden hier zentral registriert — `ccc list` und `ccc create <name>`
nutzen die `AVAILABLE_ROLES`-Map.
"""

from __future__ import annotations

from typing import Optional, Type

from ccc.roles.base import Role
from ccc.roles.pmdesk import PmDeskRole

AVAILABLE_ROLES: dict[str, Type[Role]] = {
    "pmDESK": PmDeskRole,
    # Geplant für künftige Sessions:
    # "lxcHOST":  LxcHostRole,
    # "osNGINX":  OsNginxRole,
    # "commBOX":  CommBoxRole,
}


def get_role(name: str) -> Optional[Type[Role]]:
    """Gibt die Rollen-Klasse zum Namen zurück, oder None wenn unbekannt.

    Case-insensitiv beim Lookup, aber Display bleibt case-sensitive.
    """
    for registered_name, role_class in AVAILABLE_ROLES.items():
        if registered_name.lower() == name.lower():
            return role_class
    return None
