"""marker — FIRSTBOOT_MARKER-File-Logic fuer Idempotenz-Trennung.

Marker-Datei /var/lib/xed-ccc/firstboot.applied existiert nach erstem
erfolgreichen Run. Trennt allerersten-Run-Verhalten (Skript-Defaults
greifen) von Re-Run (nur System-Ist-Zustand zaehlt — User-Wille
respektieren). Source: firstboot.sh v0.8.4 globals + main()-end.

Pattern: feedback_idempotenz_first_run_vs_rerun.md (AI035, 2026-05-03)
— Idempotenz braucht zwei Achsen, Marker-File ist die zweite.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_MARKER = Path("/var/lib/xed-ccc/firstboot.applied")


def is_first_run(marker: Path | None = None) -> bool:
    """True wenn Marker-File NICHT existiert (= noch kein erfolgreicher Run)."""
    return not (marker or DEFAULT_MARKER).exists()


def set_first_run_done(marker: Path | None = None) -> None:
    """Marker-File erstellen (mkdir parents + touch). Idempotent: erneut
    aufgerufen = no-op (Path.touch() default exist_ok=True)."""
    path = marker or DEFAULT_MARKER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
