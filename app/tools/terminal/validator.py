"""
Command validator - the deterministic classifier spec section 23
calls for: "the exact command policy should be implemented in a
deterministic validator", not decided by the LLM or by prompting.

This is pattern matching on the command STRING, run before anything
reaches subprocess. It is intentionally conservative: when in doubt
between two tiers, this module picks the more restrictive one. A
false positive (blocking something harmless) costs the user a retry;
a false negative (letting something dangerous through) could cost
real data or a compromised machine. That asymmetry is why several
patterns below are broader than the spec's literal examples.

Three tiers map onto the existing PermissionLevel enum:
  BLOCKED - never runs, regardless of confirmation (rule: some
            commands are permanently blocked - spec section 23)
  MEDIUM  - runs only with confirmation (spec section 23's
            "Potential confirmation" tier: pip install, npm install,
            git push, ...)
  LOW     - runs automatically (spec section 12: "Run Python script
            LOW"; spec section 23's low-risk examples all land here)

Nothing in this module ever returns SAFE - an arbitrary shell command
always carries more inherent risk than a pure read, even a command
that looks harmless today.
"""

from __future__ import annotations

import re

from app.tools.permissions import PermissionLevel

# --- BLOCKED: never executes, confirmation cannot override this ------------
#
# Deliberately broader than the spec's literal examples (rule: when in
# doubt, block rather than allow) - e.g. any bare "del"/"erase", not
# just "del /s", because a bare delete of an unintended file is still
# unrecoverable data loss, and section 23 groups "del" itself under
# "potentially dangerous operations".
_BLOCKED_PATTERNS = [
    re.compile(r"\bformat\s+[a-z]:", re.IGNORECASE),           # format C:
    re.compile(r"\b(del|erase)\b", re.IGNORECASE),               # any delete
    re.compile(r"\brmdir\b", re.IGNORECASE),                     # any rmdir
    re.compile(r"\brm\s+-rf?\b", re.IGNORECASE),                 # rm -rf (WSL/git-bash)
    re.compile(r"\bdiskpart\b", re.IGNORECASE),
    re.compile(r"\bchkdsk\b.*\/f", re.IGNORECASE),
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b", re.IGNORECASE),
    re.compile(r"\btakeown\b", re.IGNORECASE),
    re.compile(r"\bicacls\b.*\/grant", re.IGNORECASE),
    re.compile(r"\bnet\s+user\b.*\/active:\s*yes", re.IGNORECASE),  # re-enabling accounts
    re.compile(r"\bwevtutil\s+cl\b", re.IGNORECASE),             # clearing event logs
    re.compile(r"-executionpolicy\s+bypass", re.IGNORECASE),
    re.compile(r"\bset-executionpolicy\b", re.IGNORECASE),
    re.compile(r"\bmimikatz\b", re.IGNORECASE),
    re.compile(r"\bntds\.dit\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),                  # use system tools, not terminal
    re.compile(r"\brestart-computer\b", re.IGNORECASE),
    # Pipe-to-execute: downloads + immediately runs remote code,
    # bypassing every other check this validator does.
    re.compile(r"\|\s*(sh|bash|zsh|powershell|pwsh)\b", re.IGNORECASE),
    re.compile(r"\biex\b", re.IGNORECASE),                       # PowerShell Invoke-Expression
    re.compile(r":\(\)\s*\{.*:\|:.*\};:", re.IGNORECASE),        # classic fork bomb
]

# --- MEDIUM: runs only with confirmation ------------------------------------
_MEDIUM_PATTERNS = [
    re.compile(r"\bpip\s+(install|uninstall)\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+(install|uninstall|i)\b", re.IGNORECASE),
    re.compile(r"\byarn\s+(add|remove)\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\b", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[a-z]*f", re.IGNORECASE),
    re.compile(r"\b(choco|winget)\s+install\b", re.IGNORECASE),
    re.compile(r"\bapt(-get)?\s+(install|remove)\b", re.IGNORECASE),
]


def classify_command(command: str) -> PermissionLevel:
    """Classify a shell command string into a PermissionLevel. Never
    raises - an unparseable or empty command falls through to LOW,
    the default tier, since it will simply fail on execution."""
    if not command or not command.strip():
        return PermissionLevel.LOW

    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(command):
            return PermissionLevel.BLOCKED

    for pattern in _MEDIUM_PATTERNS:
        if pattern.search(command):
            return PermissionLevel.MEDIUM

    return PermissionLevel.LOW