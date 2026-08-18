import json
import logging

from app.config import LoggingConfig
from app.logging import get_logger, log_event, log_tool_call, redact, setup_logging


def _make_logging_config(tmp_path) -> LoggingConfig:
    return LoggingConfig(
        level="DEBUG",
        directory=str(tmp_path / "logs"),
        max_bytes=1_048_576,
        backup_count=1,
    )


def test_victor_log_file_is_created_and_contains_event(tmp_path):
    config = _make_logging_config(tmp_path)
    setup_logging(config)
    logger = get_logger("test")

    log_event(logger, logging.INFO, "unit_test_event", foo="bar")

    log_path = tmp_path / "logs" / "victor.log"
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    entry = json.loads(lines[-1])
    assert entry["message"] == "unit_test_event"
    assert entry["foo"] == "bar"
    assert entry["level"] == "INFO"


def test_error_log_only_contains_errors(tmp_path):
    config = _make_logging_config(tmp_path)
    setup_logging(config)
    logger = get_logger("test")

    log_event(logger, logging.INFO, "should_not_appear_in_errors_log")
    log_event(logger, logging.ERROR, "should_appear_in_errors_log")

    error_log_path = tmp_path / "logs" / "errors.log"
    assert error_log_path.exists()
    content = error_log_path.read_text(encoding="utf-8")
    assert "should_appear_in_errors_log" in content
    assert "should_not_appear_in_errors_log" not in content


def test_tool_calls_log_records_invocation(tmp_path):
    config = _make_logging_config(tmp_path)
    setup_logging(config)

    log_tool_call(
        tool="open_application",
        arguments={"application": "Chrome"},
        permission_level="SAFE",
        success=True,
        duration_ms=12.5,
    )

    tool_log_path = tmp_path / "logs" / "tool_calls.log"
    assert tool_log_path.exists()
    entry = json.loads(tool_log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert entry["tool"] == "open_application"
    assert entry["success"] is True
    assert entry["permission_level"] == "SAFE"


def test_redact_strips_sensitive_top_level_keys():
    fields = {"username": "victor", "password": "hunter2", "security_phrase": "x"}
    cleaned = redact(fields)
    assert cleaned["username"] == "victor"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["security_phrase"] == "[REDACTED]"


def test_redact_strips_sensitive_nested_keys():
    fields = {"request": {"api_key": "sk-12345", "url": "https://example.com"}}
    cleaned = redact(fields)
    assert cleaned["request"]["api_key"] == "[REDACTED]"
    assert cleaned["request"]["url"] == "https://example.com"


def test_secret_never_written_to_disk_even_if_logged_by_mistake(tmp_path):
    config = _make_logging_config(tmp_path)
    setup_logging(config)
    logger = get_logger("test")

    log_event(logger, logging.INFO, "accidental_log", auth_token="super-secret-value")

    log_path = tmp_path / "logs" / "victor.log"
    content = log_path.read_text(encoding="utf-8")
    assert "super-secret-value" not in content
    assert "[REDACTED]" in content
