"""
Victor configuration loading and validation.

Design notes
------------
- Configuration is YAML on disk (config/default.yaml) plus optional
  environment-variable overrides for deployment-specific values.
- All values are validated through pydantic models. A malformed or
  incomplete config fails fast at startup rather than causing silent
  misbehavior later (e.g. a missing lockout value silently disabling
  brute-force protection).
- This module never reads or stores secrets (security phrases, API
  keys, tokens). See app/auth for secret handling (Phase 3).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

DEFAULT_CONFIG_PATH = Path("config/default.yaml")
ENV_CONFIG_PATH_VAR = "VICTOR_CONFIG_PATH"
ENV_LOG_LEVEL_VAR = "VICTOR_LOG_LEVEL"
ENV_ENVIRONMENT_VAR = "VICTOR_ENV"

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class AssistantConfig(BaseModel):
    name: str = "Victor"
    address_user_as: str = "Sir"
    wake_word: str = "Victor"


class SecurityConfig(BaseModel):
    max_failed_attempts: int = Field(default=3, ge=1)
    lockout_seconds: int = Field(default=60, ge=1)
    session_timeout_minutes: int = Field(default=15, ge=1)
    secrets_path: str = "config/secrets.yaml"


class VoiceConfig(BaseModel):
    enabled: bool = False


class UIConfig(BaseModel):
    orb_enabled: bool = False


class GreetingConfig(BaseModel):
    morning_start: str = "05:00"
    afternoon_start: str = "12:00"
    evening_start: str = "17:00"
    night_start: str = "21:00"

    @field_validator(
        "morning_start", "afternoon_start", "evening_start", "night_start"
    )
    @classmethod
    def _validate_hhmm(cls, value: str) -> str:
        try:
            hours, minutes = value.split(":")
            if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                raise ValueError
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid HH:MM time value: {value!r}"
            ) from exc
        return value


class LoggingConfig(BaseModel):
    level: str = "INFO"
    directory: str = "logs"
    max_bytes: int = Field(default=5_242_880, ge=1024)
    backup_count: int = Field(default=5, ge=1)

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level {value!r}; expected one of {_VALID_LOG_LEVELS}"
            )
        return upper


class FilesystemConfig(BaseModel):
    allowed_roots: list[str] = Field(default_factory=lambda: ["~"])

    @field_validator("allowed_roots")
    @classmethod
    def _non_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("filesystem.allowed_roots must not be empty")
        return value


class ComputerConfig(BaseModel):
    # Explicit whitelist: friendly name -> launch command. Victor will
    # refuse to open/close anything not listed here, regardless of what
    # a user request or future LLM output asks for (rule 19/20).
    applications: dict[str, str] = Field(default_factory=dict)
    screenshot_directory: str = "screenshots"


class VictorConfig(BaseModel):
    """Root configuration object for Victor."""

    assistant: AssistantConfig = AssistantConfig()
    security: SecurityConfig = SecurityConfig()
    voice: VoiceConfig = VoiceConfig()
    ui: UIConfig = UIConfig()
    greeting: GreetingConfig = GreetingConfig()
    logging: LoggingConfig = LoggingConfig()
    filesystem: FilesystemConfig = FilesystemConfig()
    computer: ComputerConfig = ComputerConfig()

    model_config = {"extra": "forbid"}


class ConfigError(RuntimeError):
    """Raised when configuration cannot be loaded or fails validation."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML config at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config at {path} must be a mapping at the top level")
    return data


def load_config(path: str | Path | None = None) -> VictorConfig:
    """
    Load and validate Victor's configuration.

    Resolution order for the config file path:
      1. explicit `path` argument
      2. VICTOR_CONFIG_PATH environment variable
      3. config/default.yaml

    Environment variables VICTOR_LOG_LEVEL may override the logging
    level from the file, which is convenient for local debugging
    without editing YAML.
    """
    resolved_path = Path(
        path or os.environ.get(ENV_CONFIG_PATH_VAR) or DEFAULT_CONFIG_PATH
    )
    raw = _read_yaml(resolved_path)

    try:
        config = VictorConfig.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError, re-raised as ConfigError
        raise ConfigError(f"Invalid configuration in {resolved_path}: {exc}") from exc

    env_log_level = os.environ.get(ENV_LOG_LEVEL_VAR)
    if env_log_level:
        upper = env_log_level.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ConfigError(
                f"Invalid {ENV_LOG_LEVEL_VAR} value {env_log_level!r}; "
                f"expected one of {_VALID_LOG_LEVELS}"
            )
        config.logging.level = upper

    return config


def get_environment() -> str:
    """Return the deployment environment name (development/production/...)."""
    return os.environ.get(ENV_ENVIRONMENT_VAR, "development")
