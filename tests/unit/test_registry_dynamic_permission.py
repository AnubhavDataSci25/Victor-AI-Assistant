from pydantic import BaseModel

from app.tools.base import Tool
from app.tools.models import ToolCallRequest, ToolResult
from app.tools.permissions import PermissionLevel
from app.tools.registry import ToolRegistry


class _DynamicArgs(BaseModel):
    risky: bool = False
    model_config = {"extra": "forbid"}


class _DynamicTool(Tool):
    """A tool whose risk depends on its arguments, like run_command."""

    name = "dynamic_tool"
    description = "test tool with dynamic classification"
    permission_level = PermissionLevel.LOW  # static fallback, should be overridden
    args_model = _DynamicArgs

    def __init__(self):
        self.called = False

    def classify(self, args: BaseModel) -> PermissionLevel:
        assert isinstance(args, _DynamicArgs)
        return PermissionLevel.HIGH if args.risky else PermissionLevel.LOW

    def run(self, args: BaseModel) -> ToolResult:
        self.called = True
        return ToolResult(success=True, tool=self.name, message="ok")


def test_low_risk_invocation_executes_automatically():
    tool = _DynamicTool()
    registry = ToolRegistry()
    registry.register(tool)

    result = registry.dispatch(
        ToolCallRequest(tool="dynamic_tool", arguments={"risky": False})
    )

    assert tool.called is True
    assert result.success is True


def test_high_risk_invocation_of_same_tool_is_denied():
    tool = _DynamicTool()
    registry = ToolRegistry()
    registry.register(tool)

    result = registry.dispatch(
        ToolCallRequest(tool="dynamic_tool", arguments={"risky": True})
    )

    assert tool.called is False
    assert result.success is False
    assert result.error == "permission_denied"


def test_static_permission_level_attribute_is_unused_when_classify_overridden():
    """Confirms the registry uses classify(), not the static class
    attribute, once a tool overrides classify()."""
    tool = _DynamicTool()
    assert tool.permission_level == PermissionLevel.LOW  # static says LOW
    registry = ToolRegistry()
    registry.register(tool)

    # But this specific call is classified HIGH and must be denied,
    # proving the static attribute alone would have given the wrong answer.
    result = registry.dispatch(
        ToolCallRequest(tool="dynamic_tool", arguments={"risky": True})
    )
    assert result.success is False


def test_default_classify_falls_back_to_static_permission_level():
    """A tool that does NOT override classify() behaves exactly as before
    Phase 6 - this is the backward-compatibility guarantee."""
    from tests.unit.test_registry import _DummyTool

    tool = _DummyTool(PermissionLevel.MEDIUM)
    registry = ToolRegistry()
    registry.register(tool)

    result = registry.dispatch(ToolCallRequest(tool="dummy_tool", arguments={}))
    assert result.success is False
    assert result.error == "permission_denied"

    result_confirmed = registry.dispatch(
        ToolCallRequest(tool="dummy_tool", arguments={}), confirmed=True
    )
    assert result_confirmed.success is True