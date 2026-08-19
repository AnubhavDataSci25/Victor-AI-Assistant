"""
Victor structured logging.

Design notes
------------
- Three log files, per spec section 35:
    logs/victor.log       general application events (INFO+)
    logs/tool_calls.log   every tool invocation (dedicated logger)
    logs/errors.log       ERROR+ from anywhere in the app
- Logs are structured (JSON lines) so they can be grepped, parsed, or
  shipped to a log aggregator later without reformatting.
- A redaction filter is applied to *every* handler. It is defense in
  depth: callers should never pass secrets into log fields, but a
  filter that strips known-sensitive keys means a future bug (e.g. a
  developer accidentally logging a full request payload) doesn't
  leak a security phrase, token, or password into a log file.
- This module has no knowledge of *what* the secret is - only that
  fields with certain names must never reach disk in cleartext.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import time
from pathlib import Path
from typing import Any

from app.config import LoggingConfig

# Field names that must never be written to logs in cleartext.
# Matched case-insensitively as substrings (e.g. "user_password" is caught
# by "password").
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passphrase",
    "secret",
    "phrase",
    "token",
    "api_key",
    "apikey",
    "credential",
    "authorization",
    "auth_hash",
)
_REDACTED = "[REDACTED]"

TOOL_CALLS_LOGGER_NAME = "victor.tool_calls"


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `fields` with sensitive values replaced."""
    clean: dict[str, Any] = {}
    for key, value in fields.items():
        if _is_sensitive_key(key):
            clean[key] = _REDACTED
        elif isinstance(value, dict):
            clean[key] = redact(value)
        else:
            clean[key] = value
    return clean


class _RedactionFilter(logging.Filter):
    """Redacts sensitive values out of the structured `extra` payload."""

    def filter(self, record: logging.LogRecord) -> bool:
        payload = getattr(record, "payload", None)
        if isinstance(payload, dict):
            record.payload = redact(payload)
        return True


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for structured log files."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload = getattr(record, "payload", None)
        if isinstance(payload, dict):
            entry.update(payload)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def setup_logging(config: LoggingConfig) -> None:
    """
    Configure Victor's logging handlers. Idempotent: safe to call more
    than once (e.g. in tests) without duplicating handlers.
    """
    log_dir = Path(config.directory)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("victor")
    root.setLevel(config.level)
    for handler in root.handlers:
        handler.close()
    root.handlers.clear()
    root.propagate = False

    redaction_filter = _RedactionFilter()
    json_formatter = _JsonFormatter()

    # victor.log - general application activity
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "victor.log",
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    app_handler.setFormatter(json_formatter)
    app_handler.addFilter(redaction_filter)
    app_handler.setLevel(config.level)
    root.addHandler(app_handler)

    # errors.log - ERROR and above, from any Victor logger
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    error_handler.setFormatter(json_formatter)
    error_handler.addFilter(redaction_filter)
    error_handler.setLevel(logging.ERROR)
    root.addHandler(error_handler)

    # Console output for local development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    console_handler.addFilter(redaction_filter)
    console_handler.setLevel(config.level)
    root.addHandler(console_handler)

    # tool_calls.log - dedicated logger for every tool invocation
    tool_logger = logging.getLogger(TOOL_CALLS_LOGGER_NAME)
    tool_logger.setLevel(logging.INFO)
    for handler in tool_logger.handlers:
        handler.close()
    tool_logger.handlers.clear()
    tool_logger.propagate = True  # also flows into victor.log / console

    tool_handler = logging.handlers.RotatingFileHandler(
        log_dir / "tool_calls.log",
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
    )
    tool_handler.setFormatter(json_formatter)
    tool_handler.addFilter(redaction_filter)
    tool_handler.setLevel(logging.INFO)
    tool_logger.addHandler(tool_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced Victor logger, e.g. get_logger('brain.router')."""
    return logging.getLogger(f"victor.{name}")


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """
    Log a structured event.

    Example:
        log_event(logger, logging.INFO, "tool executed",
                  tool="open_application", success=True, duration_ms=42)

    Any field whose name matches a sensitive-key pattern is redacted
    before formatting, in addition to the filter-level safety net.
    """
    logger.log(level, message, extra={"payload": redact(fields)})


def log_tool_call(
    tool: str,
    arguments: dict[str, Any],
    permission_level: str,
    success: bool,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Convenience wrapper for the mandatory tool-call audit trail."""
    tool_logger = logging.getLogger(TOOL_CALLS_LOGGER_NAME)
    log_event(
        tool_logger,
        logging.INFO if success else logging.WARNING,
        "tool_call",
        tool=tool,
        arguments=arguments,
        permission_level=permission_level,
        success=success,
        duration_ms=duration_ms,
        error=error,
    )