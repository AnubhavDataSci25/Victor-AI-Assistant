import sys

from app.tools.permissions import PermissionLevel
from app.tools.terminal.process_manager import ProcessManager
from app.tools.terminal.tool import (
    RunCommandArgs,
    RunCommandTool,
    RunPythonArgs,
    RunPythonTool,
    StartProcessArgs,
    StartProcessTool,
    StopProcessArgs,
    StopProcessTool,
)


def test_run_command_success_captures_stdout():
    tool = RunCommandTool()
    result = tool.run(RunCommandArgs(command="echo hello"))
    assert result.success is True
    assert "hello" in result.stdout
    assert result.exit_code == 0


def test_run_command_nonzero_exit_is_failure_not_exception():
    tool = RunCommandTool()
    result = tool.run(RunCommandArgs(command="exit 3"))
    assert result.success is False
    assert result.exit_code == 3
    assert result.error == "nonzero_exit"


def test_run_command_captures_stderr():
    tool = RunCommandTool()
    result = tool.run(RunCommandArgs(command="echo oops 1>&2 && exit 1"))
    assert "oops" in result.stderr


def test_run_command_timeout():
    tool = RunCommandTool()
    result = tool.run(
        RunCommandArgs(
            command=f'{sys.executable} -c "import time; time.sleep(5)"',
            timeout_seconds=0.2,
        )
    )
    assert result.success is False
    assert result.error == "timeout"


def test_run_command_classify_matches_validator():
    tool = RunCommandTool()
    assert tool.classify(RunCommandArgs(command="pytest")) == PermissionLevel.LOW
    assert tool.classify(RunCommandArgs(command="pip install x")) == PermissionLevel.MEDIUM
    assert tool.classify(RunCommandArgs(command="del x")) == PermissionLevel.BLOCKED


def test_run_python_executes_code_and_captures_output():
    tool = RunPythonTool()
    result = tool.run(RunPythonArgs(code="print(2 + 2)"))
    assert result.success is True
    assert "4" in result.stdout


def test_run_python_captures_exception_as_failure():
    tool = RunPythonTool()
    result = tool.run(RunPythonArgs(code="raise ValueError('boom')"))
    assert result.success is False
    assert "boom" in result.stderr
    assert result.error == "nonzero_exit"


def test_run_python_is_static_low():
    tool = RunPythonTool()
    assert tool.permission_level == PermissionLevel.LOW
    assert tool.classify(RunPythonArgs(code="1")) == PermissionLevel.LOW


def test_run_python_timeout():
    tool = RunPythonTool()
    result = tool.run(RunPythonArgs(code="import time; time.sleep(5)", timeout_seconds=0.2))
    assert result.success is False
    assert result.error == "timeout"


def test_start_and_stop_process_lifecycle():
    manager = ProcessManager()
    start_tool = StartProcessTool(process_manager=manager)
    stop_tool = StopProcessTool(process_manager=manager)

    start_args = StartProcessArgs(command=f"{sys.executable} -c \"import time; time.sleep(10)\"")
    start_result = start_tool.run(start_args)
    start_result = start_tool.verify(start_args, start_result)

    assert start_result.success is True
    pid = start_result.data["pid"]
    assert manager.is_running(pid)

    stop_args = StopProcessArgs(pid=pid)
    stop_result = stop_tool.run(stop_args)
    stop_result = stop_tool.verify(stop_args, stop_result)

    assert stop_result.success is True
    assert not manager.is_running(pid)


def test_stop_process_refuses_untracked_pid():
    manager = ProcessManager()
    stop_tool = StopProcessTool(process_manager=manager)

    result = stop_tool.run(StopProcessArgs(pid=999999))

    assert result.success is False
    assert result.error == "not_tracked"


def test_start_process_classify_matches_validator():
    manager = ProcessManager()
    tool = StartProcessTool(process_manager=manager)
    assert tool.classify(StartProcessArgs(command="npm run dev")) == PermissionLevel.LOW
    assert tool.classify(StartProcessArgs(command="npm install")) == PermissionLevel.MEDIUM
