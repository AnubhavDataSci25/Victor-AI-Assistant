"""
VictorCore - orchestrates the full text-input flow:

    wake word / manual lock commands
        -> authentication challenge (if locked)
        -> router (tool call vs conversation)
        -> permission-gated dispatch (only if unlocked)
        -> humanized response

Security invariant (spec section 7, rule 10 in project memory):
tool calls NEVER execute while locked, regardless of what the router
or a future LLM produces. That check happens here, in front of the
tool registry, not inside the registry itself - the registry doesn't
know about authentication at all, and it doesn't need to.

Casual conversation is allowed while locked (spec section 13); only
tool calls are gated.
"""

from __future__ import annotations

import re

from app.auth.manager import AuthManager
from app.brain.responder import humanize
from app.brain.router import Router
from app.config import VictorConfig
from app.logging import get_logger
from app.tools.registry import ToolRegistry

logger = get_logger("brain.orchestrator")

_LOCK_COMMAND_PATTERN = re.compile(
    r"^(?:victor,?\s+)?lock(?:\s+yourself)?\.?$", re.IGNORECASE
)


class VictorCore:
    def __init__(
        self,
        config: VictorConfig,
        registry: ToolRegistry,
        auth: AuthManager,
    ) -> None:
        self._config = config
        self._registry = registry
        self._auth = auth
        self._router = Router()
        self._awaiting_phrase = False

    @property
    def _address(self) -> str:
        return self._config.assistant.address_user_as

    def handle_input(self, text: str) -> str:
        stripped = text.strip()

        if self._awaiting_phrase:
            return self._handle_phrase_attempt(stripped)

        if stripped.lower() == self._config.assistant.wake_word.lower():
            return self._handle_wake_event()

        if _LOCK_COMMAND_PATTERN.match(stripped):
            return self._handle_manual_lock()

        outcome = self._router.route(stripped)

        if outcome.kind == "conversation":
            # Harmless conversation is allowed while locked (section 13).
            return outcome.reply or f"I'm not sure how to respond to that, {self._address}."

        assert outcome.tool_call is not None

        if not self._auth.is_unlocked():
            return f"Please authenticate first, {self._address}."

        self._auth.touch_activity()
        result = self._registry.dispatch(outcome.tool_call)
        return humanize(result, address_as=self._address)

    # --- internal helpers -------------------------------------------------

    def _handle_wake_event(self) -> str:
        if self._auth.is_unlocked():
            self._auth.touch_activity()
            return f"Already verified, {self._address}. I'm ready."

        if self._auth.is_locked_out():
            remaining = self._auth.lockout_remaining_seconds()
            return (
                f"I'm temporarily locked, {self._address}. "
                f"Please try again in {remaining} seconds."
            )

        self._awaiting_phrase = True
        return f"Identity verification required, {self._address}. Please provide your security phrase."

    def _handle_phrase_attempt(self, phrase: str) -> str:
        self._awaiting_phrase = False
        result = self._auth.authenticate(phrase)

        if result.success:
            return f"{result.message} How can I help?"

        if not result.locked_out and not self._auth.is_locked_out():
            # Still have attempts left - stay in the challenge.
            self._awaiting_phrase = True

        return result.message

    def _handle_manual_lock(self) -> str:
        was_unlocked = self._auth.is_unlocked()
        self._auth.lock()
        self._awaiting_phrase = False
        if was_unlocked:
            return f"Locked, {self._address}."
        return f"Already locked, {self._address}."