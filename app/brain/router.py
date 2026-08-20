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

_OPEN_APP_PATTERNS = (
    re.compile(r"^open(?:_application)?\s+(?P<app>.+)$", re.IGNORECASE),
    re.compile(r"^launch\s+(?P<app>.+)$", re.IGNORECASE),
)

_CLOSE_APP_PATTERNS = (
    re.compile(r"^close(?:_application)?\s+(?P<app>.+)$", re.IGNORECASE),
    re.compile(r"^quit\s+(?P<app>.+)$", re.IGNORECASE),
)

_FOCUS_WINDOW_PATTERNS = (
    re.compile(r"^focus(?:_window)?\s+(?P<title>.+)$", re.IGNORECASE),
)

_SWITCH_WINDOW_PATTERNS = (
    re.compile(r"^switch(?:_window)?\s+to\s+(?P<title>.+)$", re.IGNORECASE),
)

_SCREENSHOT_PATTERNS = (
    re.compile(r"^(?:take\s+a\s+)?screenshot\.?$", re.IGNORECASE),
    re.compile(r"^take_screenshot$", re.IGNORECASE),
)

_TYPE_TEXT_PATTERNS = (
    re.compile(r"^type\s+(?P<text>.+)$", re.IGNORECASE),
)

_PRESS_KEY_PATTERNS = (
    re.compile(r"^press(?:_key)?\s+(?P<key>\S+)$", re.IGNORECASE),
)

_HOTKEY_PATTERNS = (
    re.compile(r"^hotkey\s+(?P<keys>.+)$", re.IGNORECASE),
)

_READ_FILE_PATTERNS = (
    re.compile(r"^read(?:_file)?\s+(?P<path>.+)$", re.IGNORECASE),
)

_CREATE_FILE_PATTERNS = (
    re.compile(r"^create_file\s+(?P<path>\S+)(?:\s+(?P<content>.*))?$", re.IGNORECASE),
)

_CREATE_DIR_PATTERNS = (
    re.compile(r"^(?:create|make)\s+(?:directory|folder)\s+(?P<path>.+)$", re.IGNORECASE),
)

_DELETE_FILE_PATTERNS = (
    re.compile(r"^delete_file\s+(?P<path>.+)$", re.IGNORECASE),
    re.compile(r"^delete\s+file\s+(?P<path>.+)$", re.IGNORECASE),
)

_DELETE_DIR_PATTERNS = (
    re.compile(r"^delete\s+(?:directory|folder)\s+(?P<path>.+)$", re.IGNORECASE),
)

_COPY_FILE_PATTERNS = (
    re.compile(r"^copy\s+(?P<source>.+?)\s+to\s+(?P<destination>.+)$", re.IGNORECASE),
)

_MOVE_FILE_PATTERNS = (
    re.compile(r"^move\s+(?P<source>.+?)\s+to\s+(?P<destination>.+)$", re.IGNORECASE),
)

_RENAME_FILE_PATTERNS = (
    re.compile(r"^rename\s+(?P<path>.+?)\s+to\s+(?P<new_name>.+)$", re.IGNORECASE),
)

_FIND_FILE_PATTERNS = (
    re.compile(r"^find\s+(?:file\s+)?(?P<filename>\S+)\s+in\s+(?P<path>.+)$", re.IGNORECASE),
)

_SEARCH_FILES_PATTERNS = (
    re.compile(r"^search\s+for\s+(?P<query>.+?)\s+in\s+(?P<path>.+)$", re.IGNORECASE),
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

        for pattern in _SCREENSHOT_PATTERNS:
            if pattern.match(stripped):
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(tool="take_screenshot", arguments={}),
                )

        for pattern in _OPEN_APP_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="open_application",
                        arguments={"application": match.group("app").strip()},
                    ),
                )

        for pattern in _CLOSE_APP_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="close_application",
                        arguments={"application": match.group("app").strip()},
                    ),
                )

        for pattern in _SWITCH_WINDOW_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="switch_window",
                        arguments={"title": match.group("title").strip()},
                    ),
                )

        for pattern in _FOCUS_WINDOW_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="focus_window",
                        arguments={"title": match.group("title").strip()},
                    ),
                )

        for pattern in _HOTKEY_PATTERNS:
            match = pattern.match(stripped)
            if match:
                keys = [k.strip() for k in match.group("keys").split("+") if k.strip()]
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(tool="hotkey", arguments={"keys": keys}),
                )

        for pattern in _PRESS_KEY_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="press_key", arguments={"key": match.group("key").strip()}
                    ),
                )

        for pattern in _TYPE_TEXT_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="type_text", arguments={"text": match.group("text")}
                    ),
                )

        for pattern in _CREATE_DIR_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="create_directory",
                        arguments={"path": match.group("path").strip()},
                    ),
                )

        for pattern in _CREATE_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="create_file",
                        arguments={
                            "path": match.group("path").strip(),
                            "content": (match.group("content") or "").strip(),
                        },
                    ),
                )

        for pattern in _DELETE_DIR_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="delete_directory",
                        arguments={"path": match.group("path").strip()},
                    ),
                )

        for pattern in _DELETE_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="delete_file",
                        arguments={"path": match.group("path").strip()},
                    ),
                )

        for pattern in _COPY_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="copy_file",
                        arguments={
                            "source": match.group("source").strip(),
                            "destination": match.group("destination").strip(),
                        },
                    ),
                )

        for pattern in _MOVE_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="move_file",
                        arguments={
                            "source": match.group("source").strip(),
                            "destination": match.group("destination").strip(),
                        },
                    ),
                )

        for pattern in _RENAME_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="rename_file",
                        arguments={
                            "path": match.group("path").strip(),
                            "new_name": match.group("new_name").strip(),
                        },
                    ),
                )

        for pattern in _FIND_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="find_file",
                        arguments={
                            "filename": match.group("filename").strip(),
                            "path": match.group("path").strip(),
                        },
                    ),
                )

        for pattern in _SEARCH_FILES_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="search_files",
                        arguments={
                            "query": match.group("query").strip(),
                            "path": match.group("path").strip(),
                        },
                    ),
                )

        for pattern in _READ_FILE_PATTERNS:
            match = pattern.match(stripped)
            if match:
                return RouterOutcome(
                    kind="tool_call",
                    tool_call=ToolCallRequest(
                        tool="read_file", arguments={"path": match.group("path").strip()}
                    ),
                )

        return RouterOutcome(
            kind="conversation",
            reply=(
                "I'm not able to act on that yet, Sir - my tool set is "
                "still limited. Try: \"list files in <path>\"."
            ),
        )