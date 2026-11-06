"""Part 1A endpoints (FR-010 to FR-017; research R4; task T026).

Handlers are `async def`, so every call into the (lock-free) Part 1A limiter runs on the
single event-loop thread. Accept/reject decisions, HTTP 429 and Retry-After come from
Part 1A itself; the portal only reports them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.errors import PortalError
from app.harness_results import latest_run
from app.schemas import RateLimitOutcome, RateLimitRequest

router = APIRouter()


def _registered_tier(tiers: dict, bucket) -> str | None:
    """Display-only: the tier whose capacity matches the client's bucket."""
    if bucket is None:
        return None
    return next((name for name, cfg in tiers.items() if cfg["capacity"] == bucket.capacity), None)


@router.get("/api/part-1a/tiers")
async def tiers(request: Request) -> list[dict]:
    configured = request.app.state.backends.limiter_module.TIERS
    return [
        {
            "name": name,
            "capacity": cfg["capacity"],
            "refill_per_second": cfg["refill_rate"],
            "refill_per_minute": cfg["refill_rate"] * 60,
        }
        for name, cfg in configured.items()
    ]


@router.post("/api/part-1a/request")
async def send_request(body: RateLimitRequest, request: Request) -> JSONResponse:
    state = request.app.state
    configured = state.backends.limiter_module.TIERS
    if body.tier not in configured:
        raise PortalError("invalid_input", fields=["tier"])

    limiter = state.limiter
    status_code, headers, detail = HTTPStatus.OK, None, None
    try:
        limiter.check_request(body.client_id, body.tier)
    except HTTPException as exc:
        status_code, headers, detail = exc.status_code, exc.headers, exc.detail

    bucket = limiter.clients.get(body.client_id)
    registered = _registered_tier(configured, bucket)
    retry_header = (headers or {}).get("Retry-After")
    outcome = RateLimitOutcome(
        accepted=status_code == HTTPStatus.OK,
        status_code=int(status_code),
        retry_after_seconds=int(retry_header) if retry_header and retry_header.isdigit() else None,
        detail=None if detail is None else str(detail),
        client_id=body.client_id,
        requested_tier=body.tier,
        registered_tier=registered,
        tier_mismatch=registered is not None and registered != body.tier,
        tokens_remaining=None if bucket is None else round(float(bucket.tokens), 3),
        capacity=None if bucket is None else bucket.capacity,
        timestamp_utc=datetime.now(UTC).isoformat(),
        server_instance=state.server_instance,
    )
    return JSONResponse(
        status_code=int(status_code), content=outcome.model_dump(), headers=headers
    )


@router.post("/api/part-1a/reset")
async def reset(request: Request) -> dict:
    state = request.app.state
    cleared = len(state.limiter.clients)
    state.limiter = state.backends.limiter_module.RateLimiter()
    return {"reset": True, "clients_cleared": cleared, "server_instance": state.server_instance}


@router.get("/api/part-1a/harness")
async def harness(request: Request) -> dict:
    settings = request.app.state.settings
    return latest_run(settings.part1a_harness_results, settings.max_evidence_bytes)
