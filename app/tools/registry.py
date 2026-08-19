"""
Tool registry.

This is the single choke point every tool call passes through:

    ToolCallRequest
        -> lookup tool
        -> validate arguments
        -> permission decision
        -> execute
        -> verify
        -> structured ToolResult
        -> audit log

No other path to tool execution exists in Victor. The brain layer
(router/LLM) can only ever produce a ToolCallRequest; it never touches
a Tool instance directly.
"""

from __future__ import annotations

import time

from app.logging import get_logger, log_tool_call
from app.tools.base import Tool, ToolValidationError
from app.tools.models import ToolCallRequest, ToolResult
from app.tools.permissions import PermissionDecision, PermissionEngine

logger = get_logger("tools.registry")


class ToolRegistry:
    def __init__(self, permission_engine: PermissionEngine | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._permission_engine = permission_engine or PermissionEngine()

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission_level": tool.permission_level.value,
            }
            for tool in self._tools.values()
        ]

    def dispatch(
        self, request: ToolCallRequest, confirmed: bool = False
    ) -> ToolResult:
        """
        Execute a tool call request end to end. Always returns a
        ToolResult - never raises - so callers can treat this as a
        total function.
        """
        start = time.monotonic()
        tool = self.get(request.tool)

        if tool is None:
            result = ToolResult(
                success=False,
                tool=request.tool,
                message=f"Unknown tool: {request.tool}",
                error="unknown_tool",
            )
            self._log(request, "UNKNOWN", result, start)
            return result

        try:
            args = tool.parse_arguments(request.arguments)
        except ToolValidationError as exc:
            result = ToolResult(
                success=False,
                tool=tool.name,
                message=f"Invalid arguments for {tool.name}: {exc}",
                error="invalid_arguments",
            )
            self._log(request, tool.permission_level.value, result, start)
            return result

        decision = self._permission_engine.decide(tool.permission_level, confirmed)
        if decision is not PermissionDecision.ALLOWED:
            reason = self._permission_engine.explain(tool.permission_level, decision)
            result = ToolResult(
                success=False,
                tool=tool.name,
                message=reason,
                error="permission_denied",
            )
            self._log(request, tool.permission_level.value, result, start)
            return result

        try:
            result = tool.run(args)
        except Exception as exc:  # noqa: BLE001 - deliberate safety net
            logger.exception("tool_execution_raised", extra={"payload": {"tool": tool.name}})
            result = ToolResult(
                success=False,
                tool=tool.name,
                message=f"{tool.name} failed unexpectedly: {exc}",
                error="unhandled_exception",
            )
            self._log(request, tool.permission_level.value, result, start)
            return result

        try:
            result = tool.verify(args, result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("tool_verification_raised", extra={"payload": {"tool": tool.name}})
            result = ToolResult(
                success=False,
                tool=tool.name,
                message=f"{tool.name} could not be verified: {exc}",
                error="verification_failed",
            )

        self._log(request, tool.permission_level.value, result, start)
        return result

    def _log(
        self,
        request: ToolCallRequest,
        permission_level: str,
        result: ToolResult,
        start: float,
    ) -> None:
        duration_ms = (time.monotonic() - start) * 1000
        log_tool_call(
            tool=request.tool,
            arguments=request.arguments,
            permission_level=permission_level,
            success=result.success,
            duration_ms=duration_ms,
            error=result.error,
        )