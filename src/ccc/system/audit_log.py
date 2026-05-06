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
from logging.handlers import RotatingFileHandler
from pathlib import Path

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
