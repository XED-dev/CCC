"""Base-Klasse für ccc-Rollen.

Jede Rolle erbt von `Role` und implementiert:
- description: Kurze Beschreibung
- is_implemented: True wenn vollständig
- plan(): zeigt geplante Schritte (immer)
- apply(): führt aus (nur wenn is_implemented=True)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Role(ABC):
    """Abstrakte Basis-Klasse für alle ccc-Rollen."""

    description: str = ""
    is_implemented: bool = False

    @abstractmethod
    def plan(self) -> None:
        """Zeigt die geplanten Schritte (Dry-Run, immer aufrufbar)."""

    @abstractmethod
    def apply(self) -> None:
        """Führt die Rollen-Konfiguration aus.

        Wird nur aufgerufen wenn is_implemented=True. Stubs sollen hier
        NotImplementedError werfen.
        """
