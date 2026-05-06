"""Tests fuer ccc.system.audit_log — 10 Cases."""

from __future__ import annotations

import logging
import re

import pytest

from ccc.system.audit_log import (
    init_audit_log,
    phase,
    phase_end,
    phase_start,
    verify,
)

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


# Case 5: phase_start ohne kwargs -> KEIN trailing '(...)' (Format-Robustheit)
def test_phase_start_no_ctx(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test5")
    phase_start("Phase-1-apt-install", logger=logger)
    line = next(
        ln for ln in log_file.read_text().splitlines()
        if "[PHASE] Phase-1-apt-install start" in ln
    )
    assert line.endswith("[INFO] [PHASE] Phase-1-apt-install start")
    assert ISO_PATTERN.match(line)


# Case 6: phase_start mit kwargs -> ' (k=v, k=v)'-Suffix
def test_phase_start_with_ctx(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test6")
    phase_start("Phase-2-pipx", logger=logger, target="xed-ccc", version="0.1.1")
    line = next(
        ln for ln in log_file.read_text().splitlines()
        if "[PHASE] Phase-2-pipx start" in ln
    )
    assert line.endswith(
        "[INFO] [PHASE] Phase-2-pipx start (target=xed-ccc, version=0.1.1)"
    )


# Case 7: phase_end mit rc + ctx
def test_phase_end_with_rc_and_ctx(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test7")
    phase_end("Phase-1-apt-install", rc=0, logger=logger, count=5)
    line = next(
        ln for ln in log_file.read_text().splitlines()
        if "[PHASE] Phase-1-apt-install end" in ln
    )
    assert line.endswith("[INFO] [PHASE] Phase-1-apt-install end (rc=0, count=5)")


# Case 8: verify -> '[VERIFY] <key>=<value>'
def test_verify_format(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test8")
    verify("xed-ccc-installed-version", "0.1.1", logger=logger)
    line = next(
        ln for ln in log_file.read_text().splitlines()
        if "[VERIFY]" in ln
    )
    assert line.endswith("[INFO] [VERIFY] xed-ccc-installed-version=0.1.1")
    assert ISO_PATTERN.match(line)


# Case 9: phase context-manager Happy-Path -> start + end (rc=0)
def test_phase_context_happy_path(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test9")
    with phase("ccc:demo", logger=logger, count=3):
        pass
    lines = log_file.read_text().splitlines()
    start_line = next(ln for ln in lines if "[PHASE] ccc:demo start" in ln)
    end_line = next(ln for ln in lines if "[PHASE] ccc:demo end" in ln)
    assert start_line.endswith("[INFO] [PHASE] ccc:demo start (count=3)")
    assert end_line.endswith("[INFO] [PHASE] ccc:demo end (rc=0)")


# Case 10: phase context-manager bei Exception -> end (rc=1) + re-raise
def test_phase_context_exception_path(tmp_path):
    log_file = tmp_path / "audit.log"
    logger = init_audit_log(path=log_file, namespace="test10")

    with pytest.raises(RuntimeError, match="boom"):
        with phase("ccc:demo-fail", logger=logger):
            raise RuntimeError("boom")

    lines = log_file.read_text().splitlines()
    start_line = next(ln for ln in lines if "[PHASE] ccc:demo-fail start" in ln)
    end_line = next(ln for ln in lines if "[PHASE] ccc:demo-fail end" in ln)
    assert start_line.endswith("[INFO] [PHASE] ccc:demo-fail start")
    assert end_line.endswith("[INFO] [PHASE] ccc:demo-fail end (rc=1)")
