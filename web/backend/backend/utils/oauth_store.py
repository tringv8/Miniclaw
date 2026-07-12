from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.utils.config_store import load_raw_config, save_raw_config
from backend.utils.oauth_native import (
    delete_openai_oauth_token,
    load_openai_oauth_status,
    delete_gemini_oauth_token,
    load_gemini_oauth_status,
    delete_github_copilot_token,
    load_github_copilot_status,
)

TOKEN_METHOD = "token"
BROWSER_METHOD = "browser"
DEVICE_CODE_METHOD = "device_code"

PROVIDER_CATALOG = [
    {
        "provider": "openai",
        "display_name": "OpenAI",
        "methods": [BROWSER_METHOD, DEVICE_CODE_METHOD, TOKEN_METHOD],
        "description": "Supports browser OAuth, device code, and token login.",
    },
    {
        "provider": "gemini",
        "display_name": "Google Gemini",
        "methods": [BROWSER_METHOD, TOKEN_METHOD],
        "description": "Đăng nhập qua Google OAuth2 hoặc nhập Google AI Studio API key.",
    },
    {
        "provider": "github_copilot",
        "display_name": "GitHub Copilot",
        "methods": [DEVICE_CODE_METHOD],
        "description": "Đăng nhập qua GitHub Device Code. Yêu cầu tài khoản Copilot.",
    },
    {
        "provider": "anthropic",
        "display_name": "Anthropic (Claude)",
        "methods": [TOKEN_METHOD],
        "description": "Nhập API key từ console.anthropic.com.",
    },
    {
        "provider": "google-antigravity",
        "display_name": "Google Antigravity",
        "methods": [BROWSER_METHOD],
        "description": "Uses browser OAuth for Google Cloud Code Assist.",
    },
    {
        "provider": "moonshot",
        "display_name": "Kimi (Moonshot AI)",
        "methods": [TOKEN_METHOD],
        "description": "Nhập API key từ platform.moonshot.cn.",
    },
    {
        "provider": "deepseek",
        "display_name": "DeepSeek",
        "methods": [TOKEN_METHOD],
        "description": "Nhập API key từ platform.deepseek.com.",
    },
    {
        "provider": "openrouter",
        "display_name": "OpenRouter",
        "methods": [TOKEN_METHOD],
        "description": "Nhập API key từ openrouter.ai/keys.",
    },
    {
        "provider": "ollama",
        "display_name": "Ollama (Local)",
        "methods": ["local"],
        "description": "Chạy model cục bộ qua Ollama. Không cần API key.",
    },
]


def list_provider_statuses(config_path: Path) -> list[dict[str, Any]]:
    raw = load_raw_config(config_path)
    providers = raw.get("providers") or {}
    statuses: list[dict[str, Any]] = []

    openai_oauth = detect_openai_codex_status()

    for item in PROVIDER_CATALOG:
        provider = item["provider"]
        if provider == "openai":
            block = providers.get("openai") or {}
            api_key = str(block.get("apiKey") or block.get("api_key") or "")
            token_logged_in = bool(api_key)
            oauth_logged_in = bool(openai_oauth.get("logged_in"))
            preferred = str(block.get("authMethod") or block.get("auth_method") or "").strip()
            auth_method = ""
            status = str(openai_oauth.get("status") or "not_logged_in")
            if preferred == "oauth" and oauth_logged_in:
                auth_method = "oauth"
            elif preferred == TOKEN_METHOD and token_logged_in:
                auth_method = TOKEN_METHOD
                status = "connected"
            elif token_logged_in:
                auth_method = TOKEN_METHOD
                status = "connected"
            elif oauth_logged_in:
                auth_method = "oauth"
            statuses.append(
                {
                    **item,
                    "logged_in": bool(auth_method),
                    "status": status,
                    "auth_method": auth_method,
                    "supports_token_input": True,
                    "supports_logout": token_logged_in or oauth_logged_in,
                    "account_id": openai_oauth.get("account_id", "") if auth_method == "oauth" else "",
                    "expires_at": openai_oauth.get("expires_at", "") if auth_method == "oauth" else "",
                    "help_text": item["description"],
                    "setup_command": "",
                }
            )
            continue

        if provider == "gemini":
            block = providers.get("gemini") or {}
            api_key = str(block.get("apiKey") or block.get("api_key") or "")
            token_logged_in = bool(api_key)
            gemini_oauth = load_gemini_oauth_status()
            oauth_logged_in = bool(gemini_oauth.get("logged_in"))
            preferred = str(block.get("authMethod") or block.get("auth_method") or "").strip()
            auth_method = ""
            status = str(gemini_oauth.get("status") or "not_logged_in")
            if preferred == "oauth" and oauth_logged_in:
                auth_method = "oauth"
            elif preferred == TOKEN_METHOD and token_logged_in:
                auth_method = TOKEN_METHOD
                status = "connected"
            elif token_logged_in:
                auth_method = TOKEN_METHOD
                status = "connected"
            elif oauth_logged_in:
                auth_method = "oauth"
            statuses.append(
                {
                    **item,
                    "logged_in": bool(auth_method),
                    "status": status,
                    "auth_method": auth_method,
                    "supports_token_input": True,
                    "supports_logout": token_logged_in or oauth_logged_in,
                    "account_id": gemini_oauth.get("account_id", "") if auth_method == "oauth" else "",
                    "expires_at": gemini_oauth.get("expires_at", "") if auth_method == "oauth" else "",
                    "help_text": item["description"],
                    "setup_command": "",
                }
            )
            continue

        if provider == "github_copilot":
            copilot_oauth = load_github_copilot_status()
            oauth_logged_in = bool(copilot_oauth.get("logged_in"))
            status = str(copilot_oauth.get("status") or "not_logged_in")
            statuses.append(
                {
                    **item,
                    "logged_in": oauth_logged_in,
                    "status": status,
                    "auth_method": "oauth" if oauth_logged_in else "",
                    "supports_token_input": False,
                    "supports_logout": oauth_logged_in,
                    "account_id": copilot_oauth.get("account_id", ""),
                    "expires_at": copilot_oauth.get("expires_at", ""),
                    "help_text": item["description"],
                    "setup_command": "",
                }
            )
            continue

        if provider in {"anthropic", "moonshot", "deepseek", "openrouter"}:
            block = providers.get(provider) or {}
            api_key = str(block.get("apiKey") or block.get("api_key") or "")
            statuses.append(
                {
                    **item,
                    "logged_in": bool(api_key),
                    "status": "connected" if api_key else "not_logged_in",
                    "auth_method": TOKEN_METHOD if api_key else "",
                    "supports_token_input": True,
                    "supports_logout": bool(api_key),
                    "help_text": item["description"],
                    "setup_command": "",
                }
            )
            continue

        if provider == "ollama":
            block = providers.get("ollama") or {}
            api_base = str(block.get("apiBase") or block.get("api_base") or "").strip()
            logged_in = bool(api_base)
            statuses.append(
                {
                    **item,
                    "logged_in": logged_in,
                    "status": "local" if logged_in else "not_logged_in",
                    "auth_method": "local" if logged_in else "",
                    "supports_token_input": False,
                    "supports_logout": logged_in,
                    "help_text": item["description"],
                    "setup_command": "",
                    "api_base": api_base,
                }
            )
            continue

        statuses.append(
            {
                **item,
                "logged_in": False,
                "status": "not_logged_in",
                "auth_method": "",
                "help_text": item["description"],
                "supports_token_input": False,
                "supports_logout": False,
                "setup_command": "",
            }
        )

    return statuses


def save_provider_token(config_path: Path, provider: str, token: str) -> dict[str, Any]:
    if provider not in {"openai", "anthropic", "gemini", "moonshot", "deepseek", "openrouter"}:
        raise ValueError(f"provider {provider!r} does not support token login in this launcher")
    raw = load_raw_config(config_path)
    providers = raw.setdefault("providers", {})
    block = providers.get(provider)
    if not isinstance(block, dict):
        block = {}
    block["apiKey"] = token.strip()
    block["authMethod"] = TOKEN_METHOD
    providers[provider] = block
    save_raw_config(config_path, raw)
    return {"status": "ok", "provider": provider, "method": TOKEN_METHOD}


def mark_provider_oauth(config_path: Path, provider: str) -> dict[str, Any]:
    if provider not in {"openai", "gemini"}:
        raise ValueError(f"provider {provider!r} does not support browser oauth in this launcher")
    raw = load_raw_config(config_path)
    providers = raw.setdefault("providers", {})
    block = providers.get(provider)
    if not isinstance(block, dict):
        block = {}
    block["authMethod"] = "oauth"
    providers[provider] = block
    save_raw_config(config_path, raw)
    return {"status": "ok", "provider": provider, "method": "oauth"}


def clear_provider_token(config_path: Path, provider: str) -> dict[str, Any]:
    SUPPORTED_LOGOUT_PROVIDERS = {"openai", "anthropic", "gemini", "moonshot", "deepseek", "github_copilot", "ollama", "openrouter"}
    if provider not in SUPPORTED_LOGOUT_PROVIDERS:
        raise ValueError(f"provider {provider!r} cannot be logged out from this launcher")

    if provider == "github_copilot":
        delete_github_copilot_token()
        return {"status": "ok", "provider": provider}

    raw = load_raw_config(config_path)
    providers = raw.setdefault("providers", {})
    block = providers.get(provider)
    if not isinstance(block, dict):
        block = {}
    block["apiKey"] = ""
    block["authMethod"] = ""
    if provider == "ollama":
        block["apiBase"] = ""
    providers[provider] = block
    save_raw_config(config_path, raw)

    if provider == "openai":
        delete_openai_oauth_token()
    elif provider == "gemini":
        delete_gemini_oauth_token()

    return {"status": "ok", "provider": provider}


def detect_openai_codex_status() -> dict[str, Any]:
    return load_openai_oauth_status()
