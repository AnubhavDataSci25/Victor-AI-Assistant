#!/usr/bin/env python3
"""
Provision Victor's security phrase.

Run this once (or whenever you want to change the phrase):

    python scripts/setup_auth.py

The phrase is never printed, never logged, and never stored in
plaintext - only its Argon2id hash is written to the configured
secrets file (config/secrets.yaml by default, git-ignored).
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Allow running as `python scripts/setup_auth.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.hashing import hash_phrase  # noqa: E402
from app.auth.store import SecretStore  # noqa: E402
from app.config import load_config  # noqa: E402


def main() -> int:
    config = load_config()
    store = SecretStore(config.security.secrets_path)

    if store.is_configured():
        confirm = input(
            "A security phrase is already configured. Overwrite it? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Cancelled. Existing phrase unchanged.")
            return 0

    phrase = getpass.getpass("New security phrase: ")
    if not phrase.strip():
        print("Security phrase must not be empty.", file=sys.stderr)
        return 1

    confirm_phrase = getpass.getpass("Confirm security phrase: ")
    if phrase != confirm_phrase:
        print("Phrases did not match. Nothing was saved.", file=sys.stderr)
        return 1

    store.set_phrase_hash(hash_phrase(phrase))
    # Drop references so the phrase doesn't linger in locals any longer
    # than necessary.
    del phrase, confirm_phrase

    print(f"Security phrase saved to {store.path} (Argon2id hash only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())