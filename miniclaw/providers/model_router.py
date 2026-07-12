"""Runtime model routing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from miniclaw.agent.runner import AgentRunner
from miniclaw.config.loader import get_config_path, load_config, save_config
from miniclaw.providers.base import GenerationSettings
from miniclaw.providers.openai_compat_provider import OpenAICompatProvider
from miniclaw.providers.registry import find_by_name

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_OPENROUTER_MODEL_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._:+-]*$", re.IGNORECASE)


@dataclass(frozen=True)
class ModelRouteResult:
    ok: bool
    model_id: str
    message: str


def normalize_openrouter_model_id(value: str) -> str | None:
    """Return a canonical OpenRouter model ID when the input is unambiguous."""
    model_id = value.strip()
    if model_id.lower().startswith("openrouter/"):
        model_id = model_id.split("/", 1)[1]
    if not _OPENROUTER_MODEL_ID.fullmatch(model_id):
        return None
    return model_id.lower()


async def _fetch_openrouter_model(
    api_key: str,
    model_id: str,
) -> dict[str, Any] | None:
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        response = await client.get(OPENROUTER_MODELS_URL, headers=headers)
        response.raise_for_status()
    for item in response.json().get("data", []):
        if str(item.get("id") or "").lower() == model_id:
            return item
    return None


def _sync_launcher_model_store(model_id: str, api_key: str, api_base: str) -> None:
    """Keep the launcher's model list and default selection in sync."""
    try:
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        launcher_root = repo_root / "web" / "backend"
        if str(launcher_root) not in sys.path:
            sys.path.insert(0, str(launcher_root))

        from backend.utils.model_store import (
            load_model_store,
            model_store_path_for_config,
            normalize_profile,
            save_model_store,
        )

        config_path = get_config_path()
        store_path = model_store_path_for_config(config_path)
        store = load_model_store(store_path, config_path)
        profile = normalize_profile(
            {
                "model_name": model_id,
                "model": f"openrouter/{model_id}",
                "api_key": api_key,
                "api_base": api_base,
                "auth_method": "token",
            }
        )
        for index, item in enumerate(store["models"]):
            if item.get("model_name") == model_id or item.get("model") == profile["model"]:
                store["models"][index] = normalize_profile({**item, **profile})
                break
        else:
            store["models"].append(profile)
        store["default_model"] = model_id
        save_model_store(store_path, store)
    except Exception as exc:
        logger.warning("Failed to sync OpenRouter model store: {}", exc)


async def route_openrouter_model(loop: Any, requested_model: str) -> ModelRouteResult:
    """Validate, persist, and activate an OpenRouter model for a running agent."""
    model_id = normalize_openrouter_model_id(requested_model)
    if not model_id:
        return ModelRouteResult(
            False,
            requested_model.strip(),
            "Model ID không hợp lệ. Hãy dùng định dạng `nhà-cung-cấp/tên-model`.",
        )

    config = load_config()
    provider_config = config.providers.openrouter
    if not provider_config.api_key:
        return ModelRouteResult(
            False,
            model_id,
            "Chưa cấu hình API key OpenRouter.",
        )

    try:
        model_info = await _fetch_openrouter_model(provider_config.api_key, model_id)
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Failed to query OpenRouter models: {}", exc)
        return ModelRouteResult(
            False,
            model_id,
            "Không thể kiểm tra danh sách model OpenRouter. Vui lòng thử lại.",
        )
    if model_info is None:
        return ModelRouteResult(
            False,
            model_id,
            f"Không tìm thấy model `{model_id}` trên OpenRouter.",
        )

    full_model = f"openrouter/{model_id}"
    top_provider = model_info.get("top_provider") or {}
    effective_context = int(
        top_provider.get("context_length")
        or model_info.get("context_length")
        or config.agents.defaults.context_window_tokens
    )
    supported_parameters = [
        str(param)
        for param in (model_info.get("supported_parameters") or [])
    ]
    config.agents.defaults.model = full_model
    config.agents.defaults.model_name = model_id
    config.agents.defaults.provider = "openrouter"
    config.agents.defaults.context_window_tokens = effective_context
    provider_config.model_capabilities[model_id] = supported_parameters
    save_config(config)

    spec = find_by_name("openrouter")
    api_base = config.get_api_base(full_model) or OPENROUTER_MODELS_URL.rsplit("/models", 1)[0]
    new_provider = OpenAICompatProvider(
        api_key=provider_config.api_key,
        api_base=api_base,
        default_model=full_model,
        extra_headers=provider_config.extra_headers,
        model_capabilities=provider_config.model_capabilities,
        spec=spec,
    )
    defaults = config.agents.defaults
    new_provider.generation = GenerationSettings(
        temperature=defaults.temperature,
        max_tokens=defaults.max_tokens,
        reasoning_effort=defaults.reasoning_effort,
    )

    old_provider = loop.provider
    loop.provider = new_provider
    loop.model = full_model
    loop.context_window_tokens = effective_context
    loop.runner.provider = new_provider
    loop.memory_consolidator.provider = new_provider
    loop.memory_consolidator.model = full_model
    loop.memory_consolidator.context_window_tokens = effective_context
    loop.subagents.provider = new_provider
    loop.subagents.runner = AgentRunner(new_provider)
    loop.subagents.model = full_model

    _sync_launcher_model_store(model_id, provider_config.api_key, api_base)

    old_client = getattr(old_provider, "_client", None)
    if old_client is not None and old_client is not getattr(new_provider, "_client", None):
        try:
            await old_client.close()
        except Exception:
            logger.debug("Failed to close previous LLM client", exc_info=True)

    display_name = str(model_info.get("name") or model_id)
    return ModelRouteResult(
        True,
        model_id,
        (
            f"Đã chuyển sang `{model_id}` qua OpenRouter ({display_name}). "
            f"Context window: {effective_context:,} token."
        ),
    )
