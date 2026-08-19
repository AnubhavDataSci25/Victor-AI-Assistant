"""
Assembles the ToolRegistry Victor runs with, wiring each tool to the
configuration it needs (e.g. filesystem tools get their allowed
roots). Kept separate from registry.py so the registry itself stays
agnostic of which tools exist.
"""

from __future__ import annotations

from app.config import VictorConfig
from app.tools.filesystem.path_validation import resolve_allowed_roots
from app.tools.filesystem.tool import ListDirectoryTool
from app.tools.registry import ToolRegistry


def build_registry(config: VictorConfig) -> ToolRegistry:
    registry = ToolRegistry()

    allowed_roots = resolve_allowed_roots(config.filesystem.allowed_roots)
    registry.register(ListDirectoryTool(allowed_roots=allowed_roots))

    # Later phases register computer/browser/terminal tools here.

    return registry