"""audit_log — RotatingFileHandler + UTC + Bash-Format-Kompatibilitaet.

Format identisch zu firstboot.sh v0.8.4 init_log_file() / log_to_file():
'<ISO-UTC> [LEVEL] message' → grep-Pipelines arbeiten ueber Bash- und
Python-Phasen hinweg auf derselben Datei (/var/log/xed-firstboot.log).

Run-Boundary-Marker '[INIT]' kennzeichnet jeden bootstrap-system Run-Start
(analog Bash-init_log_file Header-Block).

structlog-Migration verschoben auf eigenen Sub-Sprint nach v0.1.0-Release
(Stack-Switch + Refactor-Sprint nicht gleichzeitig — siehe TECH-STACK.md).
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterator

DEFAULT_PATH = Path("/var/log/xed-firstboot.log")
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_NAMESPACE = "xed"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def init_audit_log(
    path: Path | None = None,
    namespace: str = DEFAULT_NAMESPACE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Initialize root xed-Logger mit RotatingFileHandler.

    Buendelt: mkdir parents + RotatingFileHandler + ISO-UTC-Formatter +
    UTC-Converter (statt localtime) + Run-Boundary-Header.

    Idempotent: zweiter Aufruf erkennt existierenden Handler an Marker-
    Attribut und ueberspringt Re-Init. Kein doppelter Handler, kein
    doppeltes Logging.
    """
    logging.Formatter.converter = time.gmtime  # UTC global

    log_path = path or DEFAULT_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(namespace)

    if any(getattr(h, "_xed_audit", False) for h in logger.handlers):
        return logger

    handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    handler._xed_audit = True  # noqa: SLF001
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("[INIT] %s run start", namespace)
    return logger


def phase_start(
    name: str,
    logger: logging.Logger | None = None,
    **ctx: object,
) -> None:
    """Schreibe '[PHASE] <name> start (k=v, ...)' — Sub-Sprint-Boundary.

    ctx erlaubt Diagnose-Kontext (z.B. upgradable=N, target=xed-ccc).
    Leeres ctx -> kein trailing '(...)'.
    """
    log = logger or logging.getLogger(__name__)
    suffix = (
        " (" + ", ".join(f"{k}={v}" for k, v in ctx.items()) + ")" if ctx else ""
    )
    log.info("[PHASE] %s start%s", name, suffix)


def phase_end(
    name: str,
    rc: int = 0,
    logger: logging.Logger | None = None,
    **ctx: object,
) -> None:
    """Schreibe '[PHASE] <name> end (rc=N, k=v, ...)' — Sub-Sprint-Boundary."""
    log = logger or logging.getLogger(__name__)
    parts = [f"rc={rc}"] + [f"{k}={v}" for k, v in ctx.items()]
    log.info("[PHASE] %s end (%s)", name, ", ".join(parts))


def verify(
    key: str,
    value: object,
    logger: logging.Logger | None = None,
) -> None:
    """Schreibe '[VERIFY] <key>=<value>' — Verifikations-Snapshot.

    grep-Pattern: grep '\\[VERIFY\\] xed-ccc-installed-version=' <log>
    """
    log = logger or logging.getLogger(__name__)
    log.info("[VERIFY] %s=%s", key, value)


@contextmanager
def phase(
    name: str,
    logger: logging.Logger | None = None,
    **ctx: object,
) -> Iterator[None]:
    """Context-Manager um phase_start/phase_end-Boilerplate zu kapseln.

    Schreibt phase_start(name, **ctx) beim Eintritt, phase_end(name, rc=0)
    beim Normal-Austritt, phase_end(name, rc=1) bei Exception, dann raise.

    ctx-kwargs sind Marker-Context (z.B. count=N, tz=Europe/Vienna), NICHT
    an die gewrappte Phase-Funktion weitergegeben. Phase-Funktions-kwargs
    bleiben am natuerlichen Aufrufort innerhalb des with-Blocks.

    Beispiel:
        with phase("ccc:apply-packages", logger=log, count=len(pkgs)):
            apply_packages(pkgs, interactive=True, lang="DE", logger=log)
    """
    phase_start(name, logger=logger, **ctx)
    try:
        yield
    except Exception:
        phase_end(name, rc=1, logger=logger)
        raise
    phase_end(name, rc=0, logger=logger)
