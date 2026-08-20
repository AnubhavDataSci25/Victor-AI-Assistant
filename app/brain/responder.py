"""
Response generation: turns a structured ToolResult into the sentence
Victor actually says, per spec section 32 - never hide a meaningful
error, but never speak in raw technical terms either.
"""

from __future__ import annotations

from app.tools.models import ToolResult

_FRIENDLY_ERRORS = {
    "unknown_tool": "I don't have a tool for that yet, Sir.",
    "invalid_arguments": "I couldn't understand the details for that, Sir.",
    "permission_denied": None,  # message from PermissionEngine is already user-facing
    "path_validation_failed": "I'm not allowed to access that location, Sir.",
    "not_found": None,
    "not_a_directory": None,
    "os_permission_denied": "The operating system denied access to that, Sir.",
    "unhandled_exception": None,
    "verification_failed": None,
}


def humanize(result: ToolResult, address_as: str = "Sir") -> str:
    if result.success:
        if result.tool == "list_directory":
            entries = result.data.get("entries", [])
            if not entries:
                return f"That directory is empty, {address_as}."
            preview = ", ".join(entries[:10])
            more = f", and {len(entries) - 10} more" if len(entries) > 10 else ""
            return f"Found {len(entries)} item(s), {address_as}: {preview}{more}."

        if result.tool in ("search_files", "find_file"):
            matches = result.data.get("matches", [])
            if not matches:
                return f"No matches found, {address_as}."
            preview = ", ".join(matches[:10])
            more = f", and {len(matches) - 10} more" if len(matches) > 10 else ""
            truncated = " (results truncated)" if result.data.get("truncated") else ""
            return f"Found {len(matches)} match(es), {address_as}: {preview}{more}{truncated}."

        if result.tool == "read_file":
            content = result.data.get("content", "")
            preview = content if len(content) <= 500 else content[:500] + "..."
            return f"Here's {result.data.get('path')}, {address_as}:\n\n{preview}"

        if result.tool in ("run_command", "run_python"):
            output = (result.stdout or "").strip()
            if not output:
                return f"Done, {address_as}. No output."
            preview = output if len(output) <= 500 else output[:500] + "..."
            return f"Done, {address_as}. Output:\n\n{preview}"

        return f"Done, {address_as}. {result.message}"

    friendly = _FRIENDLY_ERRORS.get(result.error or "")
    if friendly:
        return friendly

    if result.tool in ("run_command", "run_python") and result.error == "nonzero_exit":
        stderr = (result.stderr or "").strip()
        if stderr:
            preview = stderr if len(stderr) <= 500 else stderr[:500] + "..."
            return f"{address_as}, that failed (exit code {result.exit_code}):\n\n{preview}"

    # Fall back to the tool/registry-provided message rather than hiding it.
    return f"{result.message}"