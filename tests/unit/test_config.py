from pathlib import Path

import pytest

from app.config import ConfigError, load_config

DEFAULT_CONFIG = Path("config/default.yaml")


def test_loads_default_config():
    config = load_config(DEFAULT_CONFIG)
    assert config.assistant.name == "Victor"
    assert config.assistant.address_user_as == "Sir"
    assert config.assistant.wake_word == "Victor"


def test_security_defaults_are_sane():
    config = load_config(DEFAULT_CONFIG)
    assert config.security.max_failed_attempts == 3
    assert config.security.lockout_seconds == 60
    assert config.security.session_timeout_minutes == 15


def test_missing_file_raises_config_error(tmp_path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(ConfigError):
        load_config(missing)


def test_malformed_yaml_raises_config_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("assistant: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_non_mapping_yaml_raises_config_error(tmp_path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_unknown_top_level_key_is_rejected(tmp_path):
    bad = tmp_path / "extra.yaml"
    bad.write_text("unexpected_section:\n  foo: bar\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_invalid_lockout_value_is_rejected(tmp_path):
    bad = tmp_path / "bad_security.yaml"
    bad.write_text(
        "security:\n  lockout_seconds: -5\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_invalid_greeting_time_format_is_rejected(tmp_path):
    bad = tmp_path / "bad_greeting.yaml"
    bad.write_text(
        "greeting:\n  morning_start: '25:99'\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_env_log_level_overrides_file(tmp_path, monkeypatch):
    monkeypatch.setenv("VICTOR_LOG_LEVEL", "DEBUG")
    config = load_config(DEFAULT_CONFIG)
    assert config.logging.level == "DEBUG"


def test_invalid_env_log_level_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("VICTOR_LOG_LEVEL", "NOT_A_LEVEL")
    with pytest.raises(ConfigError):
        load_config(DEFAULT_CONFIG)
