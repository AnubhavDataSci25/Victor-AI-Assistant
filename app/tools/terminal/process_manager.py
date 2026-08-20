"""
ProcessManager - tracks subprocesses started via start_process.

Critical safety boundary: stop_process is only ever allowed to
terminate a process that THIS Victor session started and is tracking
here. It cannot be handed an arbitrary system PID and asked to kill
it - that would make stop_process an unbounded process-killer, a much
larger blast radius than "stop the dev server I just started."
"""

from __future__ import annotations

import subprocess


class ProcessManager:
    def __init__(self) -> None:
        self._processes: dict[int, subprocess.Popen] = {}

    def start(self, command: str, cwd: str | None = None) -> int:
        process = subprocess.Popen(
            command,
            shell=True,  # see validator.py docstring: safety is enforced
            cwd=cwd,     # by command classification before this point,
            stdout=subprocess.PIPE,  # not by avoiding the shell.
            stderr=subprocess.PIPE,
        )
        self._processes[process.pid] = process
        return process.pid

    def is_tracked(self, pid: int) -> bool:
        return pid in self._processes

    def is_running(self, pid: int) -> bool:
        process = self._processes.get(pid)
        return process is not None and process.poll() is None

    def stop(self, pid: int, timeout_seconds: float = 5.0) -> bool:
        process = self._processes.get(pid)
        if process is None:
            return False
        if process.poll() is None:  # still running
            process.terminate()
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=timeout_seconds)
        del self._processes[pid]
        return True

    def list_tracked_pids(self) -> list[int]:
        return list(self._processes.keys())