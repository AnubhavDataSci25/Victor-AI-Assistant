from app.tools.permissions import PermissionDecision, PermissionEngine, PermissionLevel


def test_safe_is_allowed():
    engine = PermissionEngine()
    assert engine.decide(PermissionLevel.SAFE) is PermissionDecision.ALLOWED


def test_low_is_allowed():
    engine = PermissionEngine()
    assert engine.decide(PermissionLevel.LOW) is PermissionDecision.ALLOWED


def test_medium_requires_confirmation_by_default():
    engine = PermissionEngine()
    assert (
        engine.decide(PermissionLevel.MEDIUM)
        is PermissionDecision.REQUIRES_CONFIRMATION
    )


def test_high_requires_confirmation_by_default():
    engine = PermissionEngine()
    assert (
        engine.decide(PermissionLevel.HIGH) is PermissionDecision.REQUIRES_CONFIRMATION
    )


def test_medium_allowed_when_confirmed():
    engine = PermissionEngine()
    assert (
        engine.decide(PermissionLevel.MEDIUM, confirmed=True)
        is PermissionDecision.ALLOWED
    )


def test_blocked_is_always_denied_even_if_confirmed():
    engine = PermissionEngine()
    assert engine.decide(PermissionLevel.BLOCKED) is PermissionDecision.DENIED
    assert (
        engine.decide(PermissionLevel.BLOCKED, confirmed=True)
        is PermissionDecision.DENIED
    )