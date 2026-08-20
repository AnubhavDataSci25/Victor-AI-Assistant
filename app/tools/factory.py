"""
Assembles the ToolRegistry Victor runs with, wiring each tool to the
configuration it needs (e.g. filesystem tools get their allowed
roots). Kept separate from registry.py so the registry itself stays
agnostic of which tools exist.
"""

from __future__ import annotations

import logging
import platform

from app.config import VictorConfig
from app.logging import get_logger, log_event
from app.tools.computer.driver import ComputerDriver
from app.tools.computer.tool import (
    CloseApplicationTool,
    FocusWindowTool,
    HotkeyTool,
    OpenApplicationTool,
    PressKeyTool,
    SwitchWindowTool,
    TakeScreenshotTool,
    TypeTextTool,
)
from app.tools.filesystem.delete_tools import DeleteDirectoryTool, DeleteFileTool
from app.tools.filesystem.modify_tools import CopyFileTool, MoveFileTool, RenameFileTool
from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.read_tools import FindFileTool, ReadFileTool, SearchFilesTool
from app.tools.filesystem.tool import ListDirectoryTool
from app.tools.filesystem.write_tools import (
    AppendFileTool,
    CreateDirectoryTool,
    CreateFileTool,
    WriteFileTool,
)
from app.tools.registry import ToolRegistry

logger = get_logger("tools.factory")


def _build_computer_driver() -> ComputerDriver | None:
    """
    Selects the real Windows driver when running on Windows; returns
    None otherwise so computer tools are simply not registered on
    unsupported platforms (e.g. a developer's Linux/Mac machine)
    rather than crashing the whole application at startup.
    """
    if platform.system() != "Windows":
        log_event(
            logger,
            logging.WARNING,
            "computer_tools_unavailable",
            reason="unsupported_platform",
            platform=platform.system(),
        )
        return None

    from app.tools.computer.windows_driver import WindowsComputerDriver

    return WindowsComputerDriver()


_AUTO = object()  # sentinel: "pick a driver automatically based on platform"


def build_registry(
    config: VictorConfig, computer_driver: ComputerDriver | None = _AUTO  # type: ignore[assignment]
) -> ToolRegistry:
    """
    computer_driver: pass an explicit driver (e.g. FakeComputerDriver)
    for tests. Leave unset to select a real driver based on platform,
    or pass None explicitly to skip registering computer tools
    entirely.
    """
    registry = ToolRegistry()

    allowed_roots = resolve_allowed_roots(config.filesystem.allowed_roots)
    registry.register(ListDirectoryTool(allowed_roots=allowed_roots))
    registry.register(SearchFilesTool(allowed_roots=allowed_roots))
    registry.register(FindFileTool(allowed_roots=allowed_roots))
    registry.register(
        ReadFileTool(allowed_roots=allowed_roots, max_read_bytes=config.filesystem.max_read_bytes)
    )
    registry.register(CreateFileTool(allowed_roots=allowed_roots))
    registry.register(WriteFileTool(allowed_roots=allowed_roots))
    registry.register(AppendFileTool(allowed_roots=allowed_roots))
    registry.register(CreateDirectoryTool(allowed_roots=allowed_roots))
    registry.register(RenameFileTool(allowed_roots=allowed_roots))
    registry.register(CopyFileTool(allowed_roots=allowed_roots))
    registry.register(MoveFileTool(allowed_roots=allowed_roots))
    registry.register(DeleteFileTool(allowed_roots=allowed_roots))
    registry.register(DeleteDirectoryTool(allowed_roots=allowed_roots))

    driver = _build_computer_driver() if computer_driver is _AUTO else computer_driver
    if driver is not None:
        applications = config.computer.applications
        registry.register(OpenApplicationTool(driver=driver, applications=applications))
        registry.register(CloseApplicationTool(driver=driver, applications=applications))
        registry.register(FocusWindowTool(driver=driver))
        registry.register(SwitchWindowTool(driver=driver))
        registry.register(TypeTextTool(driver=driver))
        registry.register(PressKeyTool(driver=driver))
        registry.register(HotkeyTool(driver=driver))
        registry.register(TakeScreenshotTool(driver=driver))

    # Later phases register browser/terminal tools here.

    return registry