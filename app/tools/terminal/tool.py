"""
Terminal / code execution tools (spec section 22, initial set from
section 39): run_command, run_python, start_process, stop_process.

Every command that reaches subprocess has already passed through
classify_command() (see validator.py) for a permission decision, and
that decision is enforced by ToolRegistry BEFORE run() is ever called
- run() only executes once the permission engine has already said
ALLOWED. This module doesn't re-check permission; it trusts the
registry the same way every other tool does (rule 20: the registry,
not individual tools, is where the deterministic gate lives).

run_command / start_process use shell=True (see validator.py's
docstring for why - many common commands are shell builtins, not
executables). run_python instead calls the interpreter directly with
code as a single argv element, so it never goes through the shell at
all, even though it's still classified LOW like run_command's safest
tier.
"""

from __future__ import annotations

import subprocess
import sys

from pydantic import BaseModel, Field

from app.tools.base import Tool
from app.tools.models import ToolResult
from app.tools.permissions import PermissionLevel
from app.tools.terminal.process_manager import ProcessManager
from app.tools.terminal.validator import classify_command

_DEFAULT_TIMEOUT_SECONDS = 30.0
_MAX_TIMEOUT_SECONDS = 300.0
_MAX_OUTPUT_CHARS = 10_000  # avoid flooding logs/responses with huge output


def _truncate(text: str) -> str:
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    return text[:_MAX_OUTPUT_CHARS] + f"\n...[truncated, {len(text)} chars total]"


# --- run_command (dynamic LOW/MEDIUM/BLOCKED) -------------------------------


class RunCommandArgs(BaseModel):
    command: str
    cwd: str | None = None
    timeout_seconds: float = Field(default=_DEFAULT_TIMEOUT_SECONDS, gt=0, le=_MAX_TIMEOUT_SECONDS)

    model_config = {"extra": "forbid"}


class RunCommandTool(Tool):
    name = "run_command"
    description = "Run a shell command and capture its output."
    permission_level = PermissionLevel.LOW  # static fallback; classify() overrides per-call
    args_model = RunCommandArgs

    def classify(self, args: BaseModel) -> PermissionLevel:
        assert isinstance(args, RunCommandArgs)
        return classify_command(args.command)

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, RunCommandArgs)
        try:
            completed = subprocess.run(
                args.command,
                shell=True,
                cwd=args.cwd,
                capture_output=True,
                text=True,
                timeout=args.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Command timed out after {args.timeout_seconds}s, Sir.",
                error="timeout",
            )
        except OSError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Failed to run command: {exc}",
                error="os_error",
            )

        success = completed.returncode == 0
        return ToolResult(
            success=success,
            tool=self.name,
            message=(
                "Command completed." if success
                else f"Command exited with code {completed.returncode}."
            ),
            stdout=_truncate(completed.stdout),
            stderr=_truncate(completed.stderr),
            exit_code=completed.returncode,
            error=None if success else "nonzero_exit",
        )


# --- run_python (static LOW, no shell at all) --------------------------


class RunPythonArgs(BaseModel):
    code: str
    timeout_seconds: float = Field(default=_DEFAULT_TIMEOUT_SECONDS, gt=0, le=_MAX_TIMEOUT_SECONDS)

    model_config = {"extra": "forbid"}


class RunPythonTool(Tool):
    name = "run_python"
    description = "Execute a short Python snippet and capture its output."
    permission_level = PermissionLevel.LOW
    args_model = RunPythonArgs

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, RunPythonArgs)
        try:
            completed = subprocess.run(
                [sys.executable, "-c", args.code],  # argv, never shell-parsed
                capture_output=True,
                text=True,
                timeout=args.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                tool=self.name,
                message=f"Python code timed out after {args.timeout_seconds}s, Sir.",
                error="timeout",
            )
        except OSError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Failed to run Python: {exc}",
                error="os_error",
            )

        success = completed.returncode == 0
        return ToolResult(
            success=success,
            tool=self.name,
            message="Python code completed." if success else "Python code raised an error.",
            stdout=_truncate(completed.stdout),
            stderr=_truncate(completed.stderr),
            exit_code=completed.returncode,
            error=None if success else "nonzero_exit",
        )


# --- start_process / stop_process (dynamic / static LOW) -----------------


class StartProcessArgs(BaseModel):
    command: str
    cwd: str | None = None

    model_config = {"extra": "forbid"}


class StartProcessTool(Tool):
    name = "start_process"
    description = "Start a long-running background process and return its PID."
    permission_level = PermissionLevel.LOW
    args_model = StartProcessArgs

    def __init__(self, process_manager: ProcessManager) -> None:
        self._processes = process_manager

    def classify(self, args: BaseModel) -> PermissionLevel:
        assert isinstance(args, StartProcessArgs)
        return classify_command(args.command)

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, StartProcessArgs)
        try:
            pid = self._processes.start(args.command, cwd=args.cwd)
        except OSError as exc:
            return ToolResult(
                success=False, tool=self.name, message=f"Failed to start process: {exc}",
                error="os_error",
            )
        return ToolResult(
            success=True, tool=self.name,
            message=f"Started process (PID {pid}).",
            data={"pid": pid},
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        pid = result.data.get("pid")
        # A process that exits immediately (e.g. bad command) is still a
        # "started" process from our perspective - launch success is what
        # start_process promises, not that it stays alive. We only flag
        # verification failure if our own tracking somehow lost it.
        if not self._processes.is_tracked(pid):
            return ToolResult(
                success=False, tool=self.name,
                message="Process could not be tracked after starting, Sir.",
                error="verification_failed",
            )
        return result


class StopProcessArgs(BaseModel):
    pid: int

    model_config = {"extra": "forbid"}


class StopProcessTool(Tool):
    name = "stop_process"
    description = "Stop a process that Victor started with start_process."
    permission_level = PermissionLevel.LOW
    args_model = StopProcessArgs

    def __init__(self, process_manager: ProcessManager) -> None:
        self._processes = process_manager

    def run(self, args: BaseModel) -> ToolResult:
        assert isinstance(args, StopProcessArgs)
        if not self._processes.is_tracked(args.pid):
            return ToolResult(
                success=False, tool=self.name,
                message=(
                    f"PID {args.pid} wasn't started by me, Sir - I can only "
                    "stop processes I started myself."
                ),
                error="not_tracked",
            )
        self._processes.stop(args.pid)
        return ToolResult(
            success=True, tool=self.name, message=f"Stopped process (PID {args.pid}).",
            data={"pid": args.pid},
        )

    def verify(self, args: BaseModel, result: ToolResult) -> ToolResult:
        if not result.success:
            return result
        if self._processes.is_running(args.pid):
            return ToolResult(
                success=False, tool=self.name,
                message=f"Asked PID {args.pid} to stop, but it's still running, Sir.",
                error="verification_failed",
            )
        return result