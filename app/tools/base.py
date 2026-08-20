"""
Tool base class.

Every concrete tool (open_application, list_directory, run_command, ...)
subclasses Tool and declares its contract as class attributes:
name, description, permission_level, args_model. The registry is the
only thing that instantiates the args_model from raw arguments and
calls run() - individual tools never see unvalidated input.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.tools.models import ToolResult
from app.tools.permissions import PermissionLevel


class ToolValidationError(Exception):
    """Raised when raw arguments fail to validate against a tool's schema."""


class Tool(ABC):
    """Base class for every Victor tool."""

    name: str
    description: str
    permission_level: PermissionLevel
    args_model: type[BaseModel]
    timeout_seconds: float = 10.0

    def parse_arguments(self, raw_arguments: dict[str, Any]) -> BaseModel:
        """Validate raw arguments against this tool's schema."""
        try:
            return self.args_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise ToolValidationError(str(exc)) from exc

    @abstractmethod
    def run(self, args: BaseModel) -> ToolResult:
        """Execute the tool. Must not raise for expected failure modes -
        those should be captured in a failed ToolResult. Unexpected
        exceptions are still caught by the registry as a safety net."""
        raise NotImplementedError

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        """
        Optional post-execution verification hook (spec section 31):
        confirm the real-world effect actually happened rather than
        trusting run()'s return value alone. Default is a no-op;
        individual tools override this where verification is cheap
        and meaningful (e.g. checking a file now exists).
        """
        return result

    def classify(self, args: BaseModel) -> PermissionLevel:
        """
        Return the permission level for THIS specific invocation.
        Defaults to the tool's static permission_level. Override this
        when a single tool's risk depends on its arguments - e.g.
        run_command's risk depends entirely on what command was asked
        for ("python --version" vs "pip install x"). The classification
        logic itself must remain deterministic application code, never
        LLM output (rule 20).
        """
        return self.permission_level