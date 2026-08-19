"""
Security test: the security phrase must never be written to disk in
any log file, in any form - not the app log, not the tool-call log,
not the error log - regardless of whether authentication succeeds or
fails, and regardless of how many attempts are made.

This exercises the real setup_logging() + AuthManager pair together,
rather than mocking logging, because the risk being tested is an
integration mistake (a future call site accidentally interpolating
the phrase into a log message), not a unit-level one.
"""

from __future__ import annotations

from app.auth.hashing import hash_phrase
from app.auth.manager import AuthManager
from app.auth.store import SecretStore
from app.config import LoggingConfig, SecurityConfig
from app.logging import setup_logging

SECRET_PHRASE = "the-quick-brown-fox-jumps-xyz789"


def _all_log_text(log_dir) -> str:
    text = ""
    for path in log_dir.glob("*.log"):
        text += path.read_text(encoding="utf-8")
    return text


def test_phrase_never_appears_in_logs_after_mixed_auth_attempts(tmp_path):
    log_dir = tmp_path / "logs"
    setup_logging(LoggingConfig(level="DEBUG", directory=str(log_dir)))

    security_config = SecurityConfig(
        max_failed_attempts=3,
        lockout_seconds=5,
        secrets_path=str(tmp_path / "secrets.yaml"),
    )
    store = SecretStore(security_config.secrets_path)
    store.set_phrase_hash(hash_phrase(SECRET_PHRASE))
    manager = AuthManager(security_config=security_config, secret_store=store)

    # Successful attempt.
    manager.authenticate(SECRET_PHRASE)
    manager.lock()

    # Failed attempts, including ones that trigger lockout.
    manager.authenticate("wrong attempt one")
    manager.authenticate("wrong attempt two")
    manager.authenticate("wrong attempt three")
    manager.authenticate(SECRET_PHRASE)  # correct, but should be blocked by lockout

    combined = _all_log_text(log_dir)
    assert SECRET_PHRASE not in combined
    assert "wrong attempt" not in combined  # failed candidate phrases either


def test_stored_hash_file_is_not_readable_as_plaintext(tmp_path):
    store = SecretStore(tmp_path / "secrets.yaml")
    store.set_phrase_hash(hash_phrase(SECRET_PHRASE))

    raw = store.path.read_text(encoding="utf-8")
    assert SECRET_PHRASE not in raw
    assert "$argon2id$" in raw  # confirms Argon2id was actually used