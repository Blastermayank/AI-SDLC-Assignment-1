"""Application factory for the web demonstration portal (plan.md; task T015).

Run with:  python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.backends import load_backends
from app.config import Settings
from app.errors import register_error_handlers
from app.routes import health, part1a
from app.security import (
    BodySizeLimitMiddleware,
    InternalErrorMiddleware,
    RequestLogMiddleware,
    SameOriginMiddleware,
    SecurityHeadersMiddleware,
)

# Windows can map .js to text/plain in the registry; browsers refuse such module scripts.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")


def configure_logging() -> None:
    """Portal log lines only; third-party request logging stays quiet (FR-055)."""
    logger = logging.getLogger("web_demo")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    for noisy in ("httpx", "httpcore", "google_genai", "google.genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    configure_logging()
    backends = load_backends(settings)

    app = FastAPI(
        title="Assignment 1 Demonstration Portal",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.backends = backends
    app.state.limiter = backends.limiter_module.RateLimiter()
    app.state.analysis_lock = asyncio.Lock()
    app.state.server_instance = str(uuid.uuid4())

    register_error_handlers(app)

    # add_middleware puts each new middleware outside the previous one: innermost first.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(InternalErrorMiddleware)
    app.add_middleware(SameOriginMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLogMiddleware)

    app.include_router(health.router)
    app.include_router(part1a.router)

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    return app
