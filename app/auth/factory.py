"""Assembles the AuthManager from configuration, mirroring tools/factory.py."""

from __future__ import annotations

from app.auth.manager import AuthManager
from app.auth.store import SecretStore
from app.config import VictorConfig


def build_auth_manager(config: VictorConfig) -> AuthManager:
    store = SecretStore(config.security.secrets_path)
    return AuthManager(security_config=config.security, secret_store=store)