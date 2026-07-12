from __future__ import annotations

import time
from datetime import datetime, timezone
from collections.abc import Callable
from typing import Any

import httpx

from oauth_cli_kit import build_authorize_url, exchange_code_for_token, refresh_token
from oauth_cli_kit.models import OAuthToken
from oauth_cli_kit.pkce import _create_state, _generate_pkce
from oauth_cli_kit.providers import OPENAI_CODEX_PROVIDER, GOOGLE_GEMINI_PROVIDER
from oauth_cli_kit.server import _start_local_server
from oauth_cli_kit.storage import FileTokenStorage
import os
# In-memory status caches to avoid expensive file reads and synchronous OAuth refreshes
_openai_status_cache: tuple[float, dict[str, Any]] | None = None
_gemini_status_cache: tuple[float, dict[str, Any]] | None = None
_copilot_status_cache: tuple[float, dict[str, Any]] | None = None

CACHE_TTL = 5.0  # seconds

def clear_oauth_status_caches() -> None:
    global _openai_status_cache, _gemini_status_cache, _copilot_status_cache
    _openai_status_cache = None
    _gemini_status_cache = None
    _copilot_status_cache = None


def openai_provider_config():
    return OPENAI_CODEX_PROVIDER


def generate_pkce() -> tuple[str, str]:
    return _generate_pkce()


def generate_state() -> str:
    return _create_state()


def build_openai_authorize_url(
    *,
    redirect_uri: str,
    code_challenge: str,
    state: str,
) -> str:
    return build_authorize_url(
        OPENAI_CODEX_PROVIDER,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        state=state,
    )


def start_openai_callback_server(
    state: str,
    on_code: Callable[[str], None] | None = None,
):
    return _start_local_server(state, on_code=on_code)


def request_openai_device_code() -> dict[str, Any]:
    provider = OPENAI_CODEX_PROVIDER
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            provider.device_code_url,
            json={"client_id": provider.client_id},
            headers={"Content-Type": "application/json"},
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"Device code request failed: {response.status_code} {response.text}"
        )

    payload = response.json()
    device_auth_id = str(
        payload.get("device_auth_id")
        or payload.get("deviceAuthId")
        or payload.get("device_code")
        or ""
    ).strip()
    user_code = str(payload.get("user_code") or payload.get("userCode") or "").strip()
    interval = int(payload.get("interval") or 5)
    if not device_auth_id or not user_code:
        raise RuntimeError("Device code response missing required fields")

    verify_url = str(
        payload.get("verification_uri")
        or payload.get("verification_url")
        or payload.get("verify_url")
        or provider.device_verify_url
    ).strip()
    return {
        "device_auth_id": device_auth_id,
        "user_code": user_code,
        "verify_url": verify_url or provider.device_verify_url,
        "interval": interval,
    }


def poll_openai_device_code_once(device_auth_id: str, user_code: str) -> OAuthToken | None:
    provider = OPENAI_CODEX_PROVIDER
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://auth.openai.com/api/accounts/deviceauth/token",
            json={
                "client_id": provider.client_id,
                "device_auth_id": device_auth_id,
                "user_code": user_code,
            },
            headers={"Content-Type": "application/json"},
        )

    if response.status_code in {202, 204}:
        return None

    if response.status_code != 200:
        body = response.text.lower()
        if "pending" in body or "authorization_pending" in body:
            return None
        raise RuntimeError(
            f"Device code poll failed: {response.status_code} {response.text}"
        )

    payload = response.json()
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    if not access or not refresh or not isinstance(expires_in, int):
        raise RuntimeError("Device code token response missing required fields")
    account_id = payload.get("account_id")
    return OAuthToken(
        access=str(access),
        refresh=str(refresh),
        expires=int(time.time() * 1000 + expires_in * 1000),
        account_id=str(account_id) if account_id else None,
    )


def exchange_openai_code_for_token(
    *,
    code: str,
    verifier: str,
    redirect_uri: str,
) -> OAuthToken:
    return exchange_code_for_token(
        code,
        verifier,
        OPENAI_CODEX_PROVIDER,
        redirect_uri=redirect_uri,
    )


def openai_token_storage() -> FileTokenStorage:
    return FileTokenStorage(token_filename=OPENAI_CODEX_PROVIDER.token_filename)


def save_openai_oauth_token(token: OAuthToken) -> OAuthToken:
    storage = openai_token_storage()
    storage.save(token)
    return token


def delete_openai_oauth_token() -> None:
    openai_token_storage().delete()


def load_openai_oauth_status(*, min_ttl_seconds: int = 60) -> dict[str, Any]:
    global _openai_status_cache
    now = time.time()
    if _openai_status_cache is not None and (now - _openai_status_cache[0]) < CACHE_TTL:
        return _openai_status_cache[1]

    storage = openai_token_storage()
    token = storage.load()
    if not token:
        res = {"logged_in": False, "status": "not_logged_in"}
        _openai_status_cache = (now, res)
        return res

    now_ms = int(time.time() * 1000)
    if token.expires - now_ms <= min_ttl_seconds * 1000 and token.refresh:
        try:
            token = refresh_token(token.refresh, OPENAI_CODEX_PROVIDER)
            storage.save(token)
        except Exception:
            token = storage.load() or token

    now_ms = int(time.time() * 1000)
    expires_at = datetime.fromtimestamp(token.expires / 1000, tz=timezone.utc).isoformat()
    expired = token.expires <= now_ms
    res = {
        "logged_in": not expired,
        "status": "expired" if expired else "connected",
        "account_id": token.account_id or "",
        "expires_at": expires_at,
    }
    _openai_status_cache = (now, res)
    return res


def token_debug_payload() -> dict[str, Any]:
    token = openai_token_storage().load()
    if not token:
        return {}
    return {
        "access": token.access[:8],
        "refresh": token.refresh[:8],
        "expires": token.expires,
        "account_id": token.account_id,
    }


# --- Google Gemini ---

def gemini_provider_config() -> OAuthProviderConfig:
    cid = os.environ.get("MINICLAW_GEMINI_CLIENT_ID")
    if cid:
        from dataclasses import replace
        return replace(GOOGLE_GEMINI_PROVIDER, client_id=cid)
    return GOOGLE_GEMINI_PROVIDER


def build_gemini_authorize_url(
    *,
    redirect_uri: str,
    code_challenge: str,
    state: str,
) -> str:
    import urllib.parse
    config = gemini_provider_config()
    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": redirect_uri,
        "scope": config.scope,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{config.authorize_url}?{urllib.parse.urlencode(params)}"


def start_gemini_callback_server(
    state: str,
    on_code: Callable[[str], None] | None = None,
):
    return _start_local_server(state, on_code=on_code)


def exchange_gemini_code_for_token(
    *,
    code: str,
    verifier: str,
    redirect_uri: str,
) -> OAuthToken:
    return exchange_code_for_token(
        code,
        verifier,
        gemini_provider_config(),
        redirect_uri=redirect_uri,
    )


def gemini_token_storage() -> FileTokenStorage:
    return FileTokenStorage(token_filename=GOOGLE_GEMINI_PROVIDER.token_filename)


def save_gemini_oauth_token(token: OAuthToken) -> OAuthToken:
    storage = gemini_token_storage()
    storage.save(token)
    return token


def delete_gemini_oauth_token() -> None:
    gemini_token_storage().delete()


def load_gemini_oauth_status(*, min_ttl_seconds: int = 60) -> dict[str, Any]:
    global _gemini_status_cache
    now = time.time()
    if _gemini_status_cache is not None and (now - _gemini_status_cache[0]) < CACHE_TTL:
        return _gemini_status_cache[1]

    storage = gemini_token_storage()
    token = storage.load()
    if not token:
        res = {"logged_in": False, "status": "not_logged_in"}
        _gemini_status_cache = (now, res)
        return res

    now_ms = int(time.time() * 1000)
    config = gemini_provider_config()
    if token.expires - now_ms <= min_ttl_seconds * 1000 and token.refresh:
        try:
            token = refresh_token(token.refresh, config)
            storage.save(token)
        except Exception:
            token = storage.load() or token

    now_ms = int(time.time() * 1000)
    expires_at = datetime.fromtimestamp(token.expires / 1000, tz=timezone.utc).isoformat()
    expired = token.expires <= now_ms
    res = {
        "logged_in": not expired,
        "status": "expired" if expired else "connected",
        "account_id": token.account_id or "",
        "expires_at": expires_at,
    }
    _gemini_status_cache = (now, res)
    return res


# --- GitHub Copilot ---

GITHUB_COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"


def request_github_device_code() -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://github.com/login/device/code",
            json={
                "client_id": GITHUB_COPILOT_CLIENT_ID,
                "scope": "read:user",
            },
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
    if response.status_code != 200:
        raise RuntimeError(
            f"GitHub device code request failed: {response.status_code} {response.text}"
        )

    payload = response.json()
    device_code = payload.get("device_code")
    user_code = payload.get("user_code")
    verification_uri = payload.get("verification_uri")
    interval = int(payload.get("interval") or 5)

    if not device_code or not user_code or not verification_uri:
        raise RuntimeError("GitHub device code response missing required fields")

    return {
        "device_code": device_code,
        "user_code": user_code,
        "verify_url": verification_uri,
        "interval": interval,
    }


def exchange_github_copilot_session_token(github_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={
                "Authorization": f"token {github_token}",
                "User-Agent": "Miniclaw",
                "Accept": "application/json",
            },
        )
    if response.status_code != 200:
        raise RuntimeError(f"Failed to get Copilot token: {response.status_code} {response.text}")
    return response.json()


def poll_github_device_code_once(device_code: str) -> OAuthToken | None:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_COPILOT_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
    if response.status_code != 200:
        raise RuntimeError(f"GitHub device code poll failed: {response.status_code} {response.text}")

    payload = response.json()
    error = payload.get("error")
    if error:
        if error in {"authorization_pending", "slow_down"}:
            return None
        raise RuntimeError(f"GitHub device code poll returned error: {error}")

    github_token = payload.get("access_token")
    if not github_token:
        return None

    # Exchange GitHub token for Copilot token
    copilot_data = exchange_github_copilot_session_token(github_token)
    session_token = copilot_data["token"]
    expires_at = copilot_data["expires_at"]

    if isinstance(expires_at, (int, float)):
        expires_ms = int(expires_at * 1000)
    else:
        expires_ms = int((time.time() + 1500) * 1000)

    return OAuthToken(
        access=session_token,
        refresh=github_token,
        expires=expires_ms,
        account_id="copilot",
    )


def copilot_token_storage() -> FileTokenStorage:
    return FileTokenStorage(token_filename="copilot.json")


def save_github_copilot_token(token: OAuthToken) -> None:
    copilot_token_storage().save(token)


def delete_github_copilot_token() -> None:
    copilot_token_storage().delete()


def load_github_copilot_status(*, min_ttl_seconds: int = 60) -> dict[str, Any]:
    global _copilot_status_cache
    now = time.time()
    if _copilot_status_cache is not None and (now - _copilot_status_cache[0]) < CACHE_TTL:
        return _copilot_status_cache[1]

    storage = copilot_token_storage()
    token = storage.load()
    if not token:
        res = {"logged_in": False, "status": "not_logged_in"}
        _copilot_status_cache = (now, res)
        return res

    now_ms = int(time.time() * 1000)
    if token.expires - now_ms <= min_ttl_seconds * 1000 and token.refresh:
        try:
            copilot_data = exchange_github_copilot_session_token(token.refresh)
            session_token = copilot_data["token"]
            expires_at = copilot_data["expires_at"]
            if isinstance(expires_at, (int, float)):
                expires_ms = int(expires_at * 1000)
            else:
                expires_ms = int((time.time() + 1500) * 1000)

            token = OAuthToken(
                access=session_token,
                refresh=token.refresh,
                expires=expires_ms,
                account_id="copilot",
            )
            storage.save(token)
        except Exception:
            token = storage.load() or token

    now_ms = int(time.time() * 1000)
    expires_at = datetime.fromtimestamp(token.expires / 1000, tz=timezone.utc).isoformat()
    expired = token.expires <= now_ms
    res = {
        "logged_in": not expired,
        "status": "expired" if expired else "connected",
        "account_id": "copilot",
        "expires_at": expires_at,
    }
    _copilot_status_cache = (now, res)
    return res

