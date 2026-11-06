"""Evidence index and viewer (FR-040, FR-041; task T049). Read-only; lookup by ID only."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request

from app.config import Settings
from app.errors import PortalError
from app.evidence_index import GROUP_TITLES, ID_PATTERN, build_index

router = APIRouter()


def _as_dict(item, size: int) -> dict:
    return {
        "id": item.id,
        "label": item.label,
        "group": item.group,
        "part": item.part,
        "path": item.path,
        "size_bytes": size,
    }


@router.get("/api/evidence")
async def evidence_index(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    entries = build_index(settings.repo_root, settings.max_evidence_bytes)
    return {
        "groups": [
            {
                "group": group,
                "title": title,
                "items": [_as_dict(item, size) for item, size in entries if item.group == group],
            }
            for group, title in GROUP_TITLES.items()
        ]
    }


@router.get("/api/evidence/{item_id}")
async def evidence_item(item_id: str, request: Request) -> dict:
    settings: Settings = request.app.state.settings
    if not ID_PATTERN.fullmatch(item_id):
        raise PortalError("not_found")
    index = build_index(settings.repo_root, settings.max_evidence_bytes)
    item = next((entry for entry, _ in index if entry.id == item_id), None)
    if item is None:
        raise PortalError("not_found")
    try:
        raw = (settings.repo_root / item.path).read_bytes()
        content = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise PortalError("not_found") from None
    if len(raw) > settings.max_evidence_bytes:
        raise PortalError("not_found")
    return {
        **_as_dict(item, len(raw)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content": content,
    }
