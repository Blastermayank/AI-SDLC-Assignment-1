"""Error envelope and handlers (data-model.md ErrorEnvelope; FR-051; task T013).

Messages are fixed per category. Responses never contain submitted values, exception
text, stack traces, file paths or credentials.
"""

from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CATEGORIES: dict[str, tuple[int, str]] = {
    "invalid_input": (422, "The request contains invalid input."),
    "payload_too_large": (413, "The request body is larger than 64 KB."),
    "forbidden_origin": (403, "Requests from other web pages are not allowed."),
    "not_found": (404, "The requested resource was not found."),
    "busy": (409, "Another analysis is already running. Try again when it finishes."),
    "not_configured": (
        503,
        "Gemini is not configured on the server (GEMINI_API_KEY missing or rejected).",
    ),
    "quota": (429, "The Gemini quota or rate limit was reached. Try again later."),
    "service_error": (502, "The Gemini service returned an error. Try again later."),
    "network_timeout": (504, "Gemini did not respond within 60 seconds or could not be reached."),
    "invalid_model_output": (502, "Gemini returned output that failed the reviewer's validation."),
    "report_unavailable": (404, "The saved evaluation report is missing or unreadable."),
    "internal_error": (500, "Unexpected server error."),
}


class PortalError(Exception):
    """Raised by routes to return a categorised error envelope."""

    def __init__(self, category: str, fields: list[str] | None = None) -> None:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown error category: {category}")
        super().__init__(category)
        self.category = category
        self.fields = fields


def error_payload(category: str, fields: list[str] | None = None) -> dict:
    error: dict = {"category": category, "message": CATEGORIES[category][1]}
    if fields:
        error["fields"] = fields
    return {"error": error}


def error_response(
    category: str, fields: list[str] | None = None, status_code: int | None = None
) -> JSONResponse:
    status = status_code or CATEGORIES[category][0]
    return JSONResponse(status_code=status, content=error_payload(category, fields))


def _field_name(location: tuple) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path")]
    return parts[0] if parts else "body"


async def _portal_error(_request: Request, exc: PortalError) -> JSONResponse:
    return error_response(exc.category, exc.fields)


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = sorted({_field_name(tuple(err.get("loc", ()))) for err in exc.errors()})
    return error_response("invalid_input", fields)


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if exc.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED):
        return error_response("not_found", status_code=exc.status_code)
    if exc.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return error_response("internal_error", status_code=exc.status_code)
    return error_response("invalid_input", status_code=exc.status_code)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PortalError, _portal_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
