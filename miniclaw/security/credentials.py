"""Shared credential store for multi-channel tool access.

Secrets are stored in ~/.miniclaw/secrets/ as private JSON files.
LLM never sees raw secrets — only metadata (provider, status, scopes).
All tools MUST go through this module; never read secret files directly.
"""

from __future__ import annotations

import json
import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

# Valid credential statuses
STATUSES = ("connected", "expired", "revoked", "missing", "error")


class CredentialStore:
    """Abstraction layer over the secret store at ``~/.miniclaw/secrets/``."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or (Path.home() / ".miniclaw" / "secrets")
        self._base.mkdir(parents=True, exist_ok=True)
        # Best-effort restrictive permissions (no-op on Windows if unsupported)
        try:
            self._base.chmod(stat.S_IRWXU)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def save(self, user_id: str, provider: str, data: dict[str, Any]) -> None:
        """Persist a credential. *data* should contain provider-specific fields
        (e.g. access_token, refresh_token, expires_at, account, scopes)."""
        path = self._path(user_id, provider)
        payload = {
            **data,
            "_provider": provider,
            "_user_id": user_id,
            "_updated_at": _now_iso(),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._restrict(path)
        logger.debug("Credential saved: user={} provider={}", user_id, provider)

    def get(self, user_id: str, provider: str) -> dict[str, Any] | None:
        """Return the stored credential dict, or *None* if missing."""
        path = self._path(user_id, provider)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read credential {}: {}", path.name, exc)
            return None

    def delete(self, user_id: str, provider: str) -> None:
        """Remove a credential from the store."""
        path = self._path(user_id, provider)
        if path.is_file():
            path.unlink()
            logger.info("Credential deleted: user={} provider={}", user_id, provider)

    # ------------------------------------------------------------------
    # Status & metadata (safe to expose to agent)
    # ------------------------------------------------------------------

    def get_status(self, user_id: str, provider: str) -> str:
        """Return the credential status without exposing secrets."""
        data = self.get(user_id, provider)
        if data is None:
            return "missing"

        # Check explicit status override
        explicit = data.get("status")
        if explicit in STATUSES:
            return explicit

        # Derive from expires_at if present
        expires_at = data.get("expires_at")
        if expires_at is not None:
            try:
                if float(expires_at) < time.time():
                    return "expired"
            except (TypeError, ValueError):
                pass

        return "connected" if data.get("access_token") or data.get("api_key") else "error"

    def get_metadata(self, user_id: str, provider: str) -> dict[str, Any] | None:
        """Return non-secret metadata for a provider credential.

        Safe to show in TOOL_ACCOUNTS.md or system prompt.
        """
        data = self.get(user_id, provider)
        if data is None:
            return None
        return {
            "provider": provider,
            "account": data.get("account", ""),
            "status": self.get_status(user_id, provider),
            "scopes": data.get("scopes", []),
            "last_verified": data.get("last_verified", data.get("_updated_at", "")),
        }

    def list_connected(self, user_id: str) -> list[dict[str, Any]]:
        """List metadata for all credentials belonging to *user_id*."""
        results: list[dict[str, Any]] = []
        suffix = f"_{user_id}.json"
        for path in sorted(self._base.glob(f"*{suffix}")):
            provider = path.stem.removesuffix(f"_{user_id}")
            meta = self.get_metadata(user_id, provider)
            if meta:
                results.append(meta)
        return results

    # ------------------------------------------------------------------
    # Refresh support
    # ------------------------------------------------------------------

    def refresh_if_needed(self, user_id: str, provider: str) -> dict[str, Any] | None:
        """Check expiry and attempt refresh if a refresh_token exists.

        Subclass or register a provider-specific refresh callback for real
        OAuth refresh flows.  The default implementation marks the credential
        as expired when the access token has lapsed and no refresher is
        available.
        """
        data = self.get(user_id, provider)
        if data is None:
            return None

        status = self.get_status(user_id, provider)
        if status == "connected":
            return data  # Still valid

        refresh_token = data.get("refresh_token")
        refresher = self._refreshers.get(provider)

        if refresh_token and refresher:
            try:
                new_data = refresher(data)
                if new_data:
                    new_data["last_verified"] = _now_iso()
                    self.save(user_id, provider, new_data)
                    logger.info("Credential refreshed: user={} provider={}", user_id, provider)
                    return new_data
            except Exception as exc:
                logger.warning("Refresh failed for {}/{}: {}", user_id, provider, exc)

        # Mark as expired if we couldn't refresh
        if status != "expired":
            data["status"] = "expired"
            self.save(user_id, provider, data)

        return None

    # Registry for provider-specific refresh callbacks
    _refreshers: dict[str, Any] = {}

    @classmethod
    def register_refresher(cls, provider: str, fn: Any) -> None:
        """Register a callable ``fn(data) -> new_data | None`` for token refresh."""
        cls._refreshers[provider] = fn

    # ------------------------------------------------------------------
    # TOOL_ACCOUNTS.md generation
    # ------------------------------------------------------------------

    def generate_tool_accounts_md(self, user_id: str) -> str:
        """Generate TOOL_ACCOUNTS.md content from current credential state."""
        items = self.list_connected(user_id)
        if not items:
            return (
                "# Tool Accounts\n\n"
                "No tool accounts connected yet.\n"
            )

        lines = ["# Tool Accounts\n"]
        for item in items:
            provider = item["provider"]
            lines.append(f"## {provider.replace('_', ' ').title()}")
            if item.get("account"):
                lines.append(f"- Account: {item['account']}")
            lines.append(f"- Status: {item['status']}")
            if item.get("scopes"):
                scopes = item["scopes"]
                if isinstance(scopes, list):
                    scopes = ", ".join(scopes)
                lines.append(f"- Scopes: {scopes}")
            if item.get("last_verified"):
                lines.append(f"- Last verified: {item['last_verified']}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, user_id: str, provider: str) -> Path:
        safe_provider = provider.replace("/", "_").replace("\\", "_")
        safe_user = user_id.replace("/", "_").replace("\\", "_")
        return self._base / f"{safe_provider}_{safe_user}.json"

    @staticmethod
    def _restrict(path: Path) -> None:
        """Best-effort owner-only permissions."""
        try:
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
