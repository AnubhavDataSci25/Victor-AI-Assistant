"""
Victor entrypoint.

Phase 1 scope only: prove the application boots cleanly with a
validated configuration and structured logging in place. No brain,
tools, auth, or UI are wired up yet - those arrive in later phases
per the development plan.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime

from app.config import ConfigError, VictorConfig, get_environment, load_config
from app.logging import get_logger, log_event, setup_logging

logger = get_logger("main")


def deterministic_greeting(config: VictorConfig, now: datetime | None = None) -> str:
    """
    Build a time-of-day greeting from configured HH:MM boundaries.

    This is deterministic system logic, not an LLM guess (spec section 5):
    the current time always comes from the system clock, and the
    boundaries are read from config rather than hardcoded.
    """
    now = now or datetime.now()
    current = now.strftime("%H:%M")
    g = config.greeting

    if g.morning_start <= current < g.afternoon_start:
        period = "morning"
    elif g.afternoon_start <= current < g.evening_start:
        period = "afternoon"
    elif g.evening_start <= current < g.night_start:
        period = "evening"
    else:
        period = "night"

    greeting_word = "Good night" if period == "night" else f"Good {period}"
    return f"{greeting_word}, {config.assistant.address_user_as}."


def bootstrap(config_path: str | None = None) -> VictorConfig:
    """Load config and initialize logging. Raises ConfigError on failure."""
    config = load_config(config_path)
    setup_logging(config.logging)
    log_event(
        logger,
        logging.INFO,
        "victor_startup",
        environment=get_environment(),
        assistant_name=config.assistant.name,
        wake_word=config.assistant.wake_word,
        voice_enabled=config.voice.enabled,
        orb_enabled=config.ui.orb_enabled,
    )
    return config


def main() -> int:
    try:
        config = bootstrap()
    except ConfigError as exc:
        print(f"Victor failed to start: {exc}", file=sys.stderr)
        return 1

    print(f"{config.assistant.name} — {deterministic_greeting(config)}")
    print(
        f"[skeleton] environment={get_environment()} "
        f"wake_word={config.assistant.wake_word!r} "
        f"log_level={config.logging.level}"
    )
    print(
        "Phase 1 skeleton is running. "
        "No tools, authentication, or voice are active yet."
    )

    log_event(logger, logging.INFO, "victor_ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
