"""Request and response models (data-model.md; tasks T024, T031)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import CLIENT_ID_PATTERN, MAX_CODE_CHARS


class RateLimitRequest(BaseModel):
    """client_id: "1-64 chars, regex ^[A-Za-z0-9_.-]{1,64}$".

    tier: "Exactly one of the Tier.name values" - checked in the route against Part 1A's
    TIERS so the portal never keeps its own copy of the tier list.
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1, max_length=64, pattern=CLIENT_ID_PATTERN)
    tier: str = Field(min_length=1, max_length=32)


class RateLimitOutcome(BaseModel):
    accepted: bool
    status_code: int
    retry_after_seconds: int | None
    detail: str | None
    client_id: str
    requested_tier: str
    registered_tier: str | None
    tier_mismatch: bool
    tokens_remaining: float | None
    capacity: int | None
    timestamp_utc: str
    server_instance: str


class ReviewSubmission(BaseModel):
    """code: "1-20,000 characters and not whitespace-only"; never executed or stored."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)

    @field_validator("code")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code must not be empty or whitespace only")
        return value
