"""
VictorCore - the Phase 2 orchestrator tying together:

    text input -> Router -> ToolCallRequest -> ToolRegistry -> ToolResult
                          -> (or) direct conversational reply
    ToolResult -> responder.humanize() -> natural language output

This is intentionally thin. It has no state machine, no auth, no
voice - those arrive in later phases and will wrap this same core
rather than replace it.
"""

from __future__ import annotations

from app.brain.responder import humanize
from app.brain.router import Router
from app.config import VictorConfig
from app.logging import get_logger
from app.tools.registry import ToolRegistry

logger = get_logger("brain.orchestrator")


class VictorCore:
    def __init__(self, config: VictorConfig, registry: ToolRegistry) -> None:
        self._config = config
        self._registry = registry
        self._router = Router()

    def handle_input(self, text: str) -> str:
        outcome = self._router.route(text)

        if outcome.kind == "conversation":
            return outcome.reply or "I'm not sure how to respond to that, Sir."

        assert outcome.tool_call is not None
        result = self._registry.dispatch(outcome.tool_call)
        return humanize(result, address_as=self._config.assistant.address_user_as)