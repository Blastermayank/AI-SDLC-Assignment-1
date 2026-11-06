"""GET /api/health (FR-004, FR-054; task T016)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

router = APIRouter()


def gemini_key_configured() -> bool:
    """True when GEMINI_API_KEY is set; the value itself is never read into a response."""
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


@router.get("/api/health")
async def health(request: Request) -> dict:
    state = request.app.state
    return {
        "status": "ok",
        "server_instance": state.server_instance,
        "repository_url": state.settings.repository_url,
        "part1a": {"available": state.backends.limiter_module is not None},
        "part1b": {
            "module_loaded": state.backends.evaluate_module is not None,
            "configured": gemini_key_configured(),
            "model": state.backends.evaluate_module.MODEL,
        },
    }
