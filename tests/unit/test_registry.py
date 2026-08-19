from pydantic import BaseModel

from app.tools.base import Tool
from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.tool import ListDirectoryTool
from app.tools.models import ToolCallRequest, ToolResult
from app.tools.permissions import PermissionLevel
from app.tools.registry import ToolRegistry


class _NoArgs(BaseModel):
    model_config = {"extra": "forbid"}


class _DummyTool(Tool):
    """Minimal tool used only to exercise registry behavior in isolation."""

    name = "dummy_tool"
    description = "test tool"
    args_model = _NoArgs

    def __init__(self, permission_level: PermissionLevel, raises: bool = False):
        self.permission_level = permission_level
        self._raises = raises
        self.called = False

    def run(self, args: BaseModel) -> ToolResult:
        self.called = True
        if self._raises:
            raise RuntimeError("boom")
        return ToolResult(success=True, tool=self.name, message="ok")


def _registry_with(tool: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(tool)
    return registry


def test_unknown_tool_returns_failed_result_without_raising():
    registry = ToolRegistry()
    result = registry.dispatch(ToolCallRequest(tool="does_not_exist", arguments={}))
    assert result.success is False
    assert result.error == "unknown_tool"


def test_safe_tool_executes_automatically():
    tool = _DummyTool(PermissionLevel.SAFE)
    registry = _registry_with(tool)
    result = registry.dispatch(ToolCallRequest(tool="dummy_tool", arguments={}))
    assert tool.called is True
    assert result.success is True


def test_medium_tool_is_denied_without_confirmation():
    tool = _DummyTool(PermissionLevel.MEDIUM)
    registry = _registry_with(tool)
    result = registry.dispatch(ToolCallRequest(tool="dummy_tool", arguments={}))
    assert tool.called is False
    assert result.success is False
    assert result.error == "permission_denied"


def test_medium_tool_executes_when_confirmed():
    tool = _DummyTool(PermissionLevel.MEDIUM)
    registry = _registry_with(tool)
    result = registry.dispatch(
        ToolCallRequest(tool="dummy_tool", arguments={}), confirmed=True
    )
    assert tool.called is True
    assert result.success is True


def test_blocked_tool_never_executes_even_if_confirmed():
    tool = _DummyTool(PermissionLevel.BLOCKED)
    registry = _registry_with(tool)
    result = registry.dispatch(
        ToolCallRequest(tool="dummy_tool", arguments={}), confirmed=True
    )
    assert tool.called is False
    assert result.success is False
    assert result.error == "permission_denied"


def test_invalid_arguments_are_rejected_before_execution():
    tool = _DummyTool(PermissionLevel.SAFE)
    registry = _registry_with(tool)
    result = registry.dispatch(
        ToolCallRequest(tool="dummy_tool", arguments={"unexpected": "field"})
    )
    assert tool.called is False
    assert result.success is False
    assert result.error == "invalid_arguments"


def test_unhandled_exception_is_captured_as_failed_result():
    tool = _DummyTool(PermissionLevel.SAFE, raises=True)
    registry = _registry_with(tool)
    result = registry.dispatch(ToolCallRequest(tool="dummy_tool", arguments={}))
    assert result.success is False
    assert result.error == "unhandled_exception"


def test_duplicate_registration_raises():
    tool_a = _DummyTool(PermissionLevel.SAFE)
    tool_b = _DummyTool(PermissionLevel.SAFE)
    registry = _registry_with(tool_a)
    try:
        registry.register(tool_b)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_end_to_end_list_directory_through_registry(tmp_path):
    (tmp_path / "a.txt").write_text("hi")
    roots = resolve_allowed_roots([str(tmp_path)])
    registry = _registry_with(ListDirectoryTool(allowed_roots=roots))

    result = registry.dispatch(
        ToolCallRequest(tool="list_directory", arguments={"path": str(tmp_path)})
    )

    assert result.success is True
    assert "a.txt" in result.data["entries"]