from __future__ import annotations

from fastapi import APIRouter

from backend.api import articles, auth, channels, config, gateway, llm_benchmark, mini, models, oauth, sessions, skills, system, tools

router = APIRouter()
router.include_router(auth.router)
router.include_router(config.router)
router.include_router(gateway.router)
router.include_router(models.router)
router.include_router(channels.router)
router.include_router(mini.router)
router.include_router(oauth.router)
router.include_router(sessions.router)
router.include_router(skills.router)
router.include_router(tools.router)
router.include_router(system.router)
router.include_router(articles.router)
router.include_router(llm_benchmark.router)
