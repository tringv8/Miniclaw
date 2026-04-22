from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from miniclaw.providers.registry import find_by_name

from backend.utils.config_store import load_raw_config, save_raw_config

MODEL_STORE_FILE_NAME = "miniclaw-launcher-models.json"
LEGACY_MODEL_STORE_FILE_NAME = "launcher-models.json"
OPENAI_OAUTH_SUPPORTED_PROFILES = (
    {
        "model_name": "gpt-5.4",
        "model": "openai-codex/gpt-5.4",
        "api_key": "",
        "api_base": "",
        "auth_method": "oauth",
    },
    {
        "model_name": "gpt-5.3",
        "model": "openai-codex/gpt-5.3-codex",
        "api_key": "",
        "api_base": "",
        "auth_method": "oauth",
    },
    {
        "model_name": "gpt-5.2",
        "model": "openai-codex/gpt-5.2",
        "api_key": "",
        "api_base": "",
        "auth_method": "oauth",
    },
)
OPENAI_OAUTH_DEFAULT_MODEL_NAME = "gpt-5.4"
OPENAI_OAUTH_DEFAULT_MODEL = "openai-codex/gpt-5.4"
OPENAI_OAUTH_LEGACY_MODEL_NAMES = {
    "codex-mini-latest",
    "gpt-5.1-codex",
    "gpt-5.4-codex",
    "gpt-5.3-codex",
}
OPENAI_OAUTH_LEGACY_MODELS = {
    "openai-codex/codex-mini-latest",
    "openai_codex/codex-mini-latest",
    "openai-codex/gpt-5.1-codex",
    "openai_codex/gpt-5.1-codex",
}


DEFAULT_MODEL_STORE = {
    "default_model": "",
    "models": [],
}

DEFAULT_PROVIDER_MODELS: dict[tuple[str, str], dict[str, Any]] = {
    ("openai", "token"): {
        "model_name": "gpt-5.4",
        "model": "openai/gpt-5.4",
        "api_key": "",
        "api_base": "",
        "auth_method": "token",
    },
    ("openai", "oauth"): {
        "model_name": OPENAI_OAUTH_DEFAULT_MODEL_NAME,
        "model": OPENAI_OAUTH_DEFAULT_MODEL,
        "api_key": "",
        "api_base": "",
        "auth_method": "oauth",
    },
    ("anthropic", "token"): {
        "model_name": "claude-sonnet-4.6",
        "model": "anthropic/claude-sonnet-4.6",
        "api_key": "",
        "api_base": "",
        "auth_method": "token",
    },
}


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    if len(value) <= 12:
        return value[:3] + "****" + value[-2:]
    return value[:3] + "****" + value[-4:]


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "model_name": str(profile.get("model_name", "")).strip(),
        "model": str(profile.get("model", "")).strip(),
        "api_base": str(profile.get("api_base", "") or "").strip(),
        "api_key": str(profile.get("api_key", "") or "").strip(),
        "proxy": str(profile.get("proxy", "") or "").strip(),
        "auth_method": str(profile.get("auth_method", "") or "").strip(),
        "connect_mode": str(profile.get("connect_mode", "") or "").strip(),
        "workspace": str(profile.get("workspace", "") or "").strip(),
        "rpm": int(profile.get("rpm", 0) or 0),
        "max_tokens_field": str(profile.get("max_tokens_field", "") or "").strip(),
        "request_timeout": int(profile.get("request_timeout", 0) or 0),
        "thinking_level": str(profile.get("thinking_level", "") or "").strip(),
        "extra_body": profile.get("extra_body") if isinstance(profile.get("extra_body"), dict) else {},
    }


def infer_provider_name(model: str, fallback: str = "") -> str:
    raw = ""
    if "/" in model:
        raw = model.split("/", 1)[0]
    elif fallback and fallback != "auto":
        raw = fallback

    spec = find_by_name(raw)
    return spec.name if spec else raw.replace("-", "_")


def profile_from_config(config_path: Path) -> dict[str, Any] | None:
    raw = load_raw_config(config_path)
    defaults = ((raw.get("agents") or {}).get("defaults") or {})
    providers = raw.get("providers") or {}
    model_name = str(defaults.get("modelName") or defaults.get("model_name") or "").strip()
    model = str(defaults.get("model") or "").strip()
    provider_name = infer_provider_name(model or model_name, str(defaults.get("provider") or ""))
    if not model_name and not model:
        return None

    provider_block = providers.get(provider_name) or providers.get(provider_name.replace("_", "-")) or {}
    api_key = str(provider_block.get("apiKey") or provider_block.get("api_key") or "")
    api_base = str(provider_block.get("apiBase") or provider_block.get("api_base") or "")
    spec = find_by_name(provider_name)
    auth_method = "oauth" if spec and spec.is_oauth else "token"
    if spec and spec.is_oauth:
        if provider_name in {"openai_codex", "openai-codex"}:
            from backend.utils.oauth_store import detect_openai_codex_status

            auth_method = "oauth" if detect_openai_codex_status().get("logged_in") else ""
        else:
            auth_method = ""
    if spec and spec.is_local:
        auth_method = "local"

    return normalize_profile(
        {
            "model_name": model_name or model,
            "model": model or model_name,
            "api_base": api_base,
            "api_key": api_key,
            "auth_method": auth_method,
        }
    )


def model_store_path_for_config(config_path: Path) -> Path:
    return config_path.parent / MODEL_STORE_FILE_NAME


def _legacy_model_store_path(path: Path) -> Path:
    if path.name == MODEL_STORE_FILE_NAME:
        return path.with_name(LEGACY_MODEL_STORE_FILE_NAME)
    return path


def _load_store_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return deepcopy(DEFAULT_MODEL_STORE)
    return {
        "default_model": str(data.get("default_model", "")),
        "models": [normalize_profile(item) for item in data.get("models", []) if isinstance(item, dict)],
    }


def load_model_store(path: Path, config_path: Path) -> dict[str, Any]:
    if path.exists():
        store = _load_store_data(path)
    else:
        legacy_path = _legacy_model_store_path(path)
        store = _load_store_data(legacy_path) if legacy_path.exists() else deepcopy(DEFAULT_MODEL_STORE)

    changed = _sync_openai_oauth_supported_profiles(store)
    bootstrap = profile_from_config(config_path)
    if bootstrap:
        matched = False
        for index, item in enumerate(store["models"]):
            if item["model_name"] != bootstrap["model_name"]:
                continue
            merged = normalize_profile({**item, **bootstrap})
            if merged != item:
                store["models"][index] = merged
                changed = True
            matched = True
            break
        if not matched:
            store["models"].append(bootstrap)
            changed = True
        if not store["default_model"]:
            store["default_model"] = bootstrap["model_name"]
            changed = True

    if (
        not store["default_model"]
        or not any(item["model_name"] == store["default_model"] for item in store["models"])
    ) and store["models"]:
        store["default_model"] = store["models"][0]["model_name"]
        changed = True

    if changed:
        try:
            save_model_store(path, store)
        except PermissionError:
            return store
    return store


def save_model_store(path: Path, store: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "default_model": str(store.get("default_model", "")),
        "models": [normalize_profile(item) for item in store.get("models", []) if isinstance(item, dict)],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return payload


def _normalized_provider(provider: str) -> str:
    return provider.strip().lower().replace("-", "_")


def _normalized_model(model: str) -> str:
    lower = str(model or "").strip().lower()
    if lower.startswith("openai_codex/"):
        return "openai-codex/" + lower.split("/", 1)[1]
    return lower


def _openai_oauth_supported_profile_map() -> dict[str, dict[str, Any]]:
    return {
        _normalized_model(str(profile["model"])): normalize_profile(profile)
        for profile in OPENAI_OAUTH_SUPPORTED_PROFILES
    }


def _supported_openai_oauth_profile_for_model(model: str) -> dict[str, Any] | None:
    return _openai_oauth_supported_profile_map().get(_normalized_model(model))


def _is_supported_openai_oauth_model(model: str) -> bool:
    return _supported_openai_oauth_profile_for_model(model) is not None


def _is_openai_oauth_legacy_profile(profile: dict[str, Any]) -> bool:
    normalized = normalize_profile(profile)
    model = _normalized_model(normalized["model"])
    model_name = normalized["model_name"].strip().lower()
    if model in OPENAI_OAUTH_LEGACY_MODELS:
        return True
    return model.startswith("openai-codex/") and model_name in OPENAI_OAUTH_LEGACY_MODEL_NAMES


def _sync_openai_oauth_supported_profiles(store: dict[str, Any]) -> bool:
    changed = False
    supported_by_model = _openai_oauth_supported_profile_map()
    found_supported: set[str] = set()
    supported_models: list[dict[str, Any]] = []
    passthrough_models: list[dict[str, Any]] = []

    for raw_item in store.get("models", []):
        item = normalize_profile(raw_item)
        normalized_model = _normalized_model(item["model"])

        if _is_openai_oauth_legacy_profile(item):
            canonical = supported_by_model.get(normalized_model)
            if canonical is None:
                changed = True
                continue
            item = normalize_profile({**item, **canonical, "auth_method": item["auth_method"]})
            normalized_model = _normalized_model(item["model"])
            changed = True

        canonical = supported_by_model.get(normalized_model)
        if canonical:
            item = normalize_profile({**item, **canonical, "auth_method": item["auth_method"]})
            if normalized_model in found_supported:
                changed = True
                continue
            found_supported.add(normalized_model)
            supported_models.append(item)
            continue

        passthrough_models.append(item)

    ordered_supported: list[dict[str, Any]] = []
    for profile in OPENAI_OAUTH_SUPPORTED_PROFILES:
        canonical = normalize_profile(profile)
        canonical_model = _normalized_model(canonical["model"])
        matched = next(
            (item for item in supported_models if _normalized_model(item["model"]) == canonical_model),
            None,
        )
        if matched is None:
            ordered_supported.append(canonical)
            changed = True
            continue
        ordered_supported.append(matched)

    updated_models = [*ordered_supported, *passthrough_models]
    if updated_models != store.get("models", []):
        store["models"] = updated_models
        changed = True
    return changed


def _model_belongs_to_provider(provider: str, model: str, auth_method: str = "") -> bool:
    normalized_provider = _normalized_provider(provider)
    lower = _normalized_model(model)
    if normalized_provider == "openai":
        if auth_method == "oauth":
            return lower.startswith("openai-codex/") or lower.startswith("openai_codex/")
        return lower == "openai" or lower.startswith("openai/")
    if normalized_provider == "openai_codex":
        return lower.startswith("openai-codex/") or lower.startswith("openai_codex/")
    if normalized_provider == "anthropic":
        return lower == "anthropic" or lower.startswith("anthropic/")
    if normalized_provider in {"google_antigravity", "antigravity"}:
        return (
            lower == "antigravity"
            or lower == "google-antigravity"
            or lower.startswith("antigravity/")
            or lower.startswith("google-antigravity/")
        )
    return False


def _provider_family_match(provider: str, model: str) -> bool:
    normalized_provider = _normalized_provider(provider)
    if normalized_provider == "openai":
        return _model_belongs_to_provider("openai", model) or _model_belongs_to_provider(
            "openai_codex", model
        )
    return _model_belongs_to_provider(normalized_provider, model)


def _default_profile_for_provider(provider: str, auth_method: str) -> dict[str, Any] | None:
    template = DEFAULT_PROVIDER_MODELS.get((_normalized_provider(provider), auth_method))
    if not template:
        return None
    return normalize_profile(template)


def sync_provider_auth_state(
    config_path: Path,
    models_store_path: Path,
    provider: str,
    auth_method: str,
) -> dict[str, Any]:
    store = load_model_store(models_store_path, config_path)
    normalized_provider = _normalized_provider(provider)

    if normalized_provider == "openai" and auth_method == "":
        matchers = [
            lambda model: _model_belongs_to_provider("openai", model),
            lambda model: _model_belongs_to_provider("openai_codex", model),
        ]
    else:
        target_provider = "openai_codex" if normalized_provider == "openai" and auth_method == "oauth" else normalized_provider
        matchers = [lambda model, target=target_provider, method=auth_method: _model_belongs_to_provider(target, model, method)]

    found = False
    for item in store["models"]:
        if any(matcher(item.get("model", "")) for matcher in matchers):
            item["auth_method"] = auth_method
            found = True

    added_profile: dict[str, Any] | None = None
    if auth_method and not found:
        added_profile = _default_profile_for_provider(provider, auth_method)
        if added_profile:
            store["models"].append(added_profile)
            found = True

    preferred_profile: dict[str, Any] | None = None
    if normalized_provider == "openai" and auth_method == "oauth":
        _sync_openai_oauth_supported_profiles(store)
        preferred_profile = next(
            (
                item
                for item in store["models"]
                if _normalized_model(item.get("model", "")) == _normalized_model(OPENAI_OAUTH_DEFAULT_MODEL)
            ),
            None,
        )
        found = found or preferred_profile is not None

    provider_default_selected = any(
        _provider_family_match(provider, item.get("model", ""))
        and item.get("model_name") == store["default_model"]
        for item in store["models"]
    )
    default_model_missing = bool(store["default_model"]) and not any(
        item.get("model_name") == store["default_model"] for item in store["models"]
    )
    legacy_default_selected = any(
        _is_openai_oauth_legacy_profile(item) and item.get("model_name") == store["default_model"]
        for item in store["models"]
    )

    if added_profile and (
        not store["default_model"]
        or provider_default_selected
        or default_model_missing
    ):
        store["default_model"] = added_profile["model_name"]
    elif preferred_profile and (
        not store["default_model"]
        or provider_default_selected
        or legacy_default_selected
        or default_model_missing
    ):
        store["default_model"] = preferred_profile["model_name"]

    save_model_store(models_store_path, store)
    default_profile = next(
        (item for item in store["models"] if item["model_name"] == store["default_model"]),
        None,
    )
    if default_profile:
        sync_profile_to_miniclaw_config(config_path, default_profile)
    elif not store["models"]:
        raw = load_raw_config(config_path)
        agents = raw.setdefault("agents", {})
        defaults = agents.setdefault("defaults", {})
        defaults["modelName"] = ""
        defaults["model"] = ""
        defaults["provider"] = "auto"
        save_raw_config(config_path, raw)
    return store


def is_profile_configured(profile: dict[str, Any], oauth_status: dict[str, bool] | None = None) -> bool:
    auth_method = str(profile.get("auth_method") or "").strip()
    provider = infer_provider_name(str(profile.get("model") or ""), "")
    if auth_method == "oauth":
        return bool((oauth_status or {}).get(provider))
    if auth_method == "local":
        return bool(profile.get("api_base"))
    return bool(profile.get("api_key"))


def response_models(store: dict[str, Any], oauth_status: dict[str, bool] | None = None) -> dict[str, Any]:
    default_model = str(store.get("default_model", ""))
    models: list[dict[str, Any]] = []
    for index, profile in enumerate(store.get("models", [])):
        item = normalize_profile(profile)
        item.update(
            {
                "index": index,
                "api_key": mask_secret(item["api_key"]),
                "configured": is_profile_configured(item, oauth_status=oauth_status),
                "is_default": item["model_name"] == default_model,
                "is_virtual": False,
            }
        )
        models.append(item)
    openai_oauth_models = [
        item
        for item in models
        if _is_supported_openai_oauth_model(str(item.get("model") or ""))
    ]
    return {
        "models": models,
        "total": len(models),
        "default_model": default_model,
        "openai_oauth_models": openai_oauth_models,
    }


def replace_profile_secret(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = normalize_profile({**existing, **incoming})
    if not incoming.get("api_key"):
        merged["api_key"] = str(existing.get("api_key", ""))
    return merged


def sync_profile_to_miniclaw_config(config_path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    raw = load_raw_config(config_path)
    agents = raw.setdefault("agents", {})
    defaults = agents.setdefault("defaults", {})
    providers = raw.setdefault("providers", {})

    normalized = normalize_profile(profile)
    provider_name = infer_provider_name(normalized["model"], str(defaults.get("provider") or ""))

    defaults["modelName"] = normalized["model_name"]
    defaults["model"] = normalized["model"]
    defaults["provider"] = provider_name or "auto"

    spec = find_by_name(provider_name)
    if provider_name and not (spec and spec.is_oauth):
        block = providers.get(provider_name)
        if not isinstance(block, dict):
            block = {}
        block["apiKey"] = normalized["api_key"]
        if normalized["api_base"]:
            block["apiBase"] = normalized["api_base"]
        elif "apiBase" in block:
            block.pop("apiBase", None)
        providers[provider_name] = block

    return save_raw_config(config_path, raw)
