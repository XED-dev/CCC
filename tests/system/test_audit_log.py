"""Tests fuer ccc.system.audit_log — 4 Cases."""

from __future__ import annotations

import logging
import re

import pytest

from ccc.system.audit_log import init_audit_log

ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \[\w+\] ")


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Raeume Test-Logger nach jedem Case (verhindert Handler-Leak zwischen Cases)."""
    yield
    for name in list(logging.Logger.manager.loggerDict):
        logger = logging.getLogger(name)
        for h in list(logger.handlers):
            h.close()
            logger.removeHandler(h)


# Case 1: init_audit_log schreibt Run-Header in ISO-Format + [INIT]
def test_init_writes_header(tmp_path):
    log_file = tmp_path / "audit.log"
    init_audit_log(path=log_file, namespace="test1")
    content = log_file.read_text()
    assert "[INIT] test1 run start" in content
    first_line = content.splitlines()[0]
    assert ISO_PATTERN.match(first_line), f"first line nicht im ISO-Format: {first_line!r}"


# Case 2: Logger-Records werden im erwarteten Bash-kompatiblen Format geschrieben
def test_logger_format_matches_bash(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test2")
    logger.info("hello world")
    logger.error("boom")
    lines = log_file.read_text().splitlines()
    # Filter ueber Inhalt, nicht Level — INIT-Header hat selbst Level [INFO]
    info_line = next(line for line in lines if "hello world" in line)
    error_line = next(line for line in lines if "boom" in line)
    assert info_line.endswith("[INFO] hello world")
    assert error_line.endswith("[ERROR] boom")
    assert ISO_PATTERN.match(info_line)
    assert ISO_PATTERN.match(error_line)


# Case 3: RotatingFileHandler triggert bei klein-gesetztem max_bytes
def test_rotation_triggers(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(
        path=log_file, namespace="test3",
        max_bytes=200, backup_count=2,
    )
    for i in range(50):
        logger.info("padding line %d with extra text to fill bytes", i)
    assert (tmp_path / "audit.log.1").exists()


# Case 4: Re-Init = Append, kein Overwrite (Forensik-Trail bleibt) + Idempotenz-Schutz
def test_reinit_appends_no_overwrite(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test4")
    logger.info("first run record")
    handler_count_first = len(logger.handlers)

    logger = init_audit_log(path=log_file, namespace="test4")
    logger.info("second run record")

    content = log_file.read_text()
    assert "first run record" in content
    assert "second run record" in content
    assert len(logger.handlers) == handler_count_first
