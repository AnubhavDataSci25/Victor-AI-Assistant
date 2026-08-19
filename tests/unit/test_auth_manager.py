from app.auth.hashing import hash_phrase
from app.auth.manager import AuthManager
from app.auth.store import SecretStore
from app.config import SecurityConfig

PHRASE = "correct phrase"


class _FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _manager(tmp_path, clock, **security_overrides):
    defaults = dict(
        max_failed_attempts=3,
        lockout_seconds=60,
        session_timeout_minutes=15,
        secrets_path=str(tmp_path / "secrets.yaml"),
    )
    defaults.update(security_overrides)
    config = SecurityConfig(**defaults)
    store = SecretStore(config.secrets_path)
    store.set_phrase_hash(hash_phrase(PHRASE))
    return AuthManager(security_config=config, secret_store=store, clock=clock)


def test_starts_locked(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    assert manager.is_unlocked() is False


def test_correct_phrase_unlocks(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    result = manager.authenticate(PHRASE)
    assert result.success is True
    assert manager.is_unlocked() is True


def test_wrong_phrase_stays_locked(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    result = manager.authenticate("wrong")
    assert result.success is False
    assert manager.is_unlocked() is False


def test_third_consecutive_failure_triggers_lockout(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    manager.authenticate("wrong 1")
    manager.authenticate("wrong 2")
    result = manager.authenticate("wrong 3")

    assert result.locked_out is True
    assert manager.is_locked_out() is True


def test_correct_phrase_rejected_during_lockout(tmp_path):
    clock = _FakeClock()
    manager = _manager(tmp_path, clock)
    manager.authenticate("wrong 1")
    manager.authenticate("wrong 2")
    manager.authenticate("wrong 3")

    result = manager.authenticate(PHRASE)
    assert result.success is False
    assert result.locked_out is True


def test_lockout_expires_after_configured_seconds(tmp_path):
    clock = _FakeClock()
    manager = _manager(tmp_path, clock, lockout_seconds=60)
    manager.authenticate("wrong 1")
    manager.authenticate("wrong 2")
    manager.authenticate("wrong 3")
    assert manager.is_locked_out() is True

    clock.advance(61)
    assert manager.is_locked_out() is False

    result = manager.authenticate(PHRASE)
    assert result.success is True


def test_successful_auth_resets_failed_attempt_counter(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    manager.authenticate("wrong 1")
    manager.authenticate(PHRASE)  # success resets counter
    manager.authenticate("wrong again")
    manager.authenticate("wrong again 2")
    # Should NOT be locked out yet - counter was reset by the success.
    assert manager.is_locked_out() is False


def test_session_times_out_after_inactivity(tmp_path):
    clock = _FakeClock()
    manager = _manager(tmp_path, clock, session_timeout_minutes=15)
    manager.authenticate(PHRASE)
    assert manager.is_unlocked() is True

    clock.advance(15 * 60 + 1)
    assert manager.is_unlocked() is False


def test_touch_activity_extends_session(tmp_path):
    clock = _FakeClock()
    manager = _manager(tmp_path, clock, session_timeout_minutes=15)
    manager.authenticate(PHRASE)

    clock.advance(14 * 60)
    manager.touch_activity()
    clock.advance(14 * 60)  # would have expired without the touch

    assert manager.is_unlocked() is True


def test_manual_lock_ends_session_immediately(tmp_path):
    manager = _manager(tmp_path, _FakeClock())
    manager.authenticate(PHRASE)
    assert manager.is_unlocked() is True

    manager.lock()
    assert manager.is_unlocked() is False


def test_authenticate_before_provisioning_fails_safely(tmp_path):
    config = SecurityConfig(secrets_path=str(tmp_path / "never_created.yaml"))
    store = SecretStore(config.secrets_path)
    manager = AuthManager(security_config=config, secret_store=store, clock=_FakeClock())

    result = manager.authenticate("anything")
    assert result.success is False
    assert manager.is_unlocked() is False