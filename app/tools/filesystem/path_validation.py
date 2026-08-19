"""
Path validation for filesystem tools (spec section 21, rule 7).

Every filesystem tool must resolve and validate a path through this
module before touching disk. This is intentionally strict and boring:
- Resolves symlinks and ".." segments (Path.resolve()) so a crafted
  path like "~/../../etc/passwd" can't sneak past a naive prefix check.
- Requires the resolved path to sit inside one of the configured
  allowed roots.
- Never trusts the caller's string representation of the path - only
  the resolved, absolute result.
"""

from __future__ import annotations

import os
from pathlib import Path


class PathValidationError(Exception):
    """Raised when a requested path falls outside allowed roots."""


def _expand_user_path(raw_path: str) -> Path:
    if raw_path == "~" or raw_path.startswith(("~/", "~\\")):
        home = Path(os.environ.get("HOME") or Path.home())
        return home / raw_path[2:]
    return Path(raw_path).expanduser()


def resolve_allowed_roots(raw_roots: list[str]) -> list[Path]:
    return [_expand_user_path(root).resolve() for root in raw_roots]


def validate_path(raw_path: str, allowed_roots: list[Path]) -> Path:
    """
    Resolve `raw_path` and confirm it lives under one of the allowed
    roots. Returns the resolved, absolute Path on success. Raises
    PathValidationError otherwise.
    """
    if not raw_path or not raw_path.strip():
        raise PathValidationError("Path must not be empty")

    candidate = _expand_user_path(raw_path).resolve()

    for root in allowed_roots:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        else:
            return candidate

    raise PathValidationError(
        f"Path {raw_path!r} resolves outside of Victor's allowed directories"
    )