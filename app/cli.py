"""
Text-based interactive Victor. Run with: python -m app.cli

This is the Phase 2 deliverable made runnable: a REPL loop where text
input goes through the router, tool registry, and responder exactly as
it will once voice (Phase 8) and the orb UI (Phase 10) are layered on
top of the same VictorCore.
"""

from __future__ import annotations

from app.brain.orchestrator import VictorCore
from app.main import bootstrap
from app.tools.factory import build_registry


def run() -> int:
    config = bootstrap()
    registry = build_registry(config)
    core = VictorCore(config, registry)

    print(f"{config.assistant.name} is listening (text mode). Type 'exit' to quit.")
    print('Try: list files in ~')

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if text.lower() in {"exit", "quit"}:
            break
        if not text:
            continue

        print(core.handle_input(text))

    return 0


if __name__ == "__main__":
    raise SystemExit(run())