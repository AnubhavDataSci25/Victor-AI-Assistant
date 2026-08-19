from app.auth.session import Session


class _FakeClock:
    def __init__(self, start: float = 0.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_inactive_before_start():
    session = Session(timeout_seconds=60, clock=_FakeClock())
    assert session.is_active() is False


def test_active_immediately_after_start():
    session = Session(timeout_seconds=60, clock=_FakeClock())
    session.start()
    assert session.is_active() is True


def test_expires_after_timeout(tmp_path=None):
    clock = _FakeClock()
    session = Session(timeout_seconds=60, clock=clock)
    session.start()

    clock.advance(61)
    assert session.is_active() is False


def test_extend_resets_the_clock():
    clock = _FakeClock()
    session = Session(timeout_seconds=60, clock=clock)
    session.start()

    clock.advance(50)
    session.extend()
    clock.advance(50)  # 100s total, but only 50s since extend

    assert session.is_active() is True


def test_end_deactivates_immediately():
    clock = _FakeClock()
    session = Session(timeout_seconds=60, clock=clock)
    session.start()
    session.end()
    assert session.is_active() is False


def test_remaining_seconds_counts_down():
    clock = _FakeClock()
    session = Session(timeout_seconds=60, clock=clock)
    session.start()
    clock.advance(10)
    assert 49 <= session.remaining_seconds() <= 50