"""
Router - stands in for the LLM's intent/tool-selection role
(spec section 17) until real LLM orchestration (Ollama) is wired up.

IMPORTANT: this is a deliberately temporary, deterministic stub. It
exists so the full chain - text in, tool call out, permission check,
execution, structured response - can be proven end to end (Phase 2
deliverable) without a network dependency on a local model server.

When the real LLM integration lands, this module's public contract
(RouterOutcome, route()) stays the same; only the implementation of
route() changes from regex matching to an LLM call that emits the
same ToolCallRequest shape. Nothing downstream needs to change,
which is the point of routing everything through ToolCallRequest
rather than letting free-form text reach the tool layer directly.

Per rule 19, this stub's output is not implicitly trusted: it can
only ever produce a ToolCallRequest, which still has to pass through
ToolRegistry validation and the permission engine like any other
tool call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.tools.models import ToolCallRequest

_LIST_DIR_PATTERNS = (
    re.compile(r"^list_directory\s+(?P<path>.+)$", re.IGNORECASE),
    re.compile(
        r"^(?:list|show)\s+(?:the\s+)?(?:files?|contents?)\s+(?:in|of)\s+(?P<path>.+)$",
        re.IGNORECASE,
    ),
    re.compile(r"^what(?:'s| is)\s+in\s+(?P<path>.+)\??$", re.IGNORECASE),
)

_SMALL_TALK: dict[re.Pattern[str], str] = {
    re.compile(r"^how are you\??$", re.IGNORECASE): (
        "I'm doing well, Sir. What are we working on?"
    ),
    re.compile(r"^who are you\??$", re.IGNORECASE): (
        "I'm Victor, Sir. Your personal AI assistant."
    ),
    re.compile(r"^what can you do\??$", re.IGNORECASE): (
        "Right now I can hold a conversation and list directory "
        "contents, Sir. More capabilities are on the way."
    ),
}


@dataclass
class RouterOutcome:
    kind: Literal["tool_call", "conversation"]
    tool_call: ToolCallRequest | None = None
    reply: str | None = None


class Router:
    """Classifies user text as a tool call or plain conversation."""

    def route(self, text: str) -> RouterOutcome:
        stripped = text.strip()
        if not stripped:
            return RouterOutcome(
                kind="conversation", reply="I didn't catch that, Sir."
            )

        for pattern, reply in _SMALL_TALK.items():
            if pattern.match(stripped):
                return RouterOutcome(kind="conversation", reply=reply)

        for pattern in _LIST_DIR_PATTERNS:
            match = pattern.match(stripped)
            if match:
                path = match.group("path").strip().strip('"').strip("'")
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="list_directory", arguments={"path": path}
                    ),
                )

        return RouterOutcome(
            kind="conversation",
            reply=(
                "I'm not able to act on that yet, Sir - my tool set is "
                "still limited. Try: \"list files in <path>\"."
            ),
        )