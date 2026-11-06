"""Part 1B live analysis (FR-020 to FR-028; research R5-R7; task T032).

The analysis is performed by Part 1B's own reviewer (`analyze_code`, imported through the
evaluation harness module). The live Layer 1/2 checks reuse the harness's RESPONSE_SCHEMA
and invariant_check; nothing here re-implements prompting, validation or scoring.
"""

from __future__ import annotations

import asyncio
import json
import time
from http import HTTPStatus

import httpx
from fastapi import APIRouter, Request
from google.genai import errors as genai_errors

from app.errors import PortalError
from app.routes.health import gemini_key_configured
from app.schemas import ReviewSubmission

router = APIRouter()

LAYER3_REASON = (
    "Requires ground truth: Layer 3 compares findings with the expected category of a "
    "dataset case, so it runs only in the evaluation harness."
)
_AUTH_FAILURES = (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN)


def classify_failure(exc: BaseException) -> str:
    """Map an exception to a portal error category (research R5) by type and status code."""
    if isinstance(exc, genai_errors.ClientError):
        if exc.code == HTTPStatus.TOO_MANY_REQUESTS:
            return "quota"
        if exc.code in _AUTH_FAILURES:
            return "not_configured"
        return "service_error"
    if isinstance(exc, genai_errors.APIError):
        return "service_error"
    if isinstance(exc, (TimeoutError, httpx.TransportError)):
        return "network_timeout"
    # ValueError / RuntimeError raised by the reviewer's own response validation.
    return "invalid_model_output"


def live_checks(evaluate, result: dict, code: str) -> dict:
    """Layer 1 and Layer 2 exactly as the evaluation harness computes them."""
    try:
        evaluate.validate(instance=result, schema=evaluate.RESPONSE_SCHEMA)
        layer1 = {"passed": True, "errors": []}
    except evaluate.ValidationError as exc:
        layer1 = {"passed": False, "errors": [exc.message]}

    if layer1["passed"]:
        violations = evaluate.invariant_check(result, code)
        layer2 = {"passed": not violations, "errors": violations}
    else:
        layer2 = {"passed": False, "errors": ["Not evaluated because Layer 1 failed."]}

    return {
        "layer1": layer1,
        "layer2": layer2,
        "layer3": {"applicable": False, "reason": LAYER3_REASON},
    }


@router.post("/api/part-1b/analyze")
async def analyze(body: ReviewSubmission, request: Request) -> dict:
    state = request.app.state
    evaluate = state.backends.evaluate_module
    lock: asyncio.Lock = state.analysis_lock

    if lock.locked():
        raise PortalError("busy")
    if not gemini_key_configured():
        raise PortalError("not_configured")

    async with lock:
        started = time.perf_counter()
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(evaluate.analyze_code, body.code),
                timeout=state.settings.analysis_timeout_s,
            )
        except (
            genai_errors.APIError,
            httpx.TransportError,
            TimeoutError,
            ValueError,
            RuntimeError,
        ) as exc:
            raise PortalError(classify_failure(exc)) from None
        elapsed_ms = round((time.perf_counter() - started) * 1000)

    result = json.loads(raw)
    return {
        "model": evaluate.MODEL,
        "elapsed_ms": elapsed_ms,
        "result": result,
        "raw": raw,
        "live_checks": live_checks(evaluate, result, body.code),
    }
