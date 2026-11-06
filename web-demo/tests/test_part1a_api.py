"""Part 1A through the real limiter (FR-010 to FR-016, SC-002, SC-003; task T021)."""

import pytest
from fastapi import HTTPException

URL = "/api/part-1a/request"


def send(client, client_id, tier):
    return client.post(URL, json={"client_id": client_id, "tier": tier})


def test_limiter_is_the_part1a_class(app):
    assert isinstance(app.state.limiter, app.state.backends.limiter_module.RateLimiter)


def test_tiers_are_read_from_part1a(client, app):
    configured = app.state.backends.limiter_module.TIERS
    body = client.get("/api/part-1a/tiers").json()
    assert [tier["name"] for tier in body] == list(configured)
    for tier in body:
        source = configured[tier["name"]]
        assert tier["capacity"] == source["capacity"]
        assert tier["refill_per_second"] == pytest.approx(source["refill_rate"])
        assert tier["refill_per_minute"] == pytest.approx(source["refill_rate"] * 60)


@pytest.mark.parametrize("client_id", [f"sc002-client-{n}" for n in range(10)])
def test_free_tier_accepts_five_then_returns_429(client, client_id):
    instance = client.get("/api/health").json()["server_instance"]
    for _ in range(5):
        response = send(client, client_id, "free")
        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] is True
        assert body["status_code"] == 200
        assert body["retry_after_seconds"] is None
        assert body["server_instance"] == instance

    response = send(client, client_id, "free")
    assert response.status_code == 429
    body = response.json()
    assert body["accepted"] is False
    assert body["status_code"] == 429
    assert int(response.headers["retry-after"]) >= 1
    assert body["retry_after_seconds"] == int(response.headers["retry-after"])


def test_retry_after_header_is_passed_through_unchanged(client, app, monkeypatch):
    limiter = app.state.limiter
    original = limiter.check_request
    raised = []

    def spy(client_id, tier="free"):
        try:
            return original(client_id, tier)
        except HTTPException as exc:
            raised.append(exc)
            raise

    monkeypatch.setattr(limiter, "check_request", spy)
    for _ in range(5):
        send(client, "spy-client", "free")
    response = send(client, "spy-client", "free")

    assert len(raised) == 1
    assert response.headers["retry-after"] == raised[0].headers["Retry-After"]
    assert response.json()["detail"] == raised[0].detail


def test_limits_are_isolated_per_client(client):
    for _ in range(6):
        send(client, "noisy-client", "free")
    response = send(client, "quiet-client", "free")
    assert response.status_code == 200
    assert response.json()["accepted"] is True


def test_tier_is_fixed_by_first_request(client):
    send(client, "tier-client", "free")
    body = send(client, "tier-client", "premium").json()
    assert body["requested_tier"] == "premium"
    assert body["registered_tier"] == "free"
    assert body["tier_mismatch"] is True
    assert body["capacity"] == 5


def test_tokens_remaining_reported_from_bucket(client, app):
    body = send(client, "token-client", "standard").json()
    bucket = app.state.limiter.clients["token-client"]
    assert body["tokens_remaining"] == pytest.approx(round(bucket.tokens, 3))
    assert body["capacity"] == 20


def test_reset_clears_buckets_but_not_tiers(client, app):
    tiers_before = client.get("/api/part-1a/tiers").json()
    for client_id in ("reset-a", "reset-b", "reset-c"):
        send(client, client_id, "free")

    body = client.post("/api/part-1a/reset").json()

    assert body["reset"] is True
    assert body["clients_cleared"] == 3
    assert app.state.limiter.clients == {}
    assert client.get("/api/part-1a/tiers").json() == tiers_before
    for _ in range(5):
        assert send(client, "reset-a", "free").status_code == 200


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"client_id": "", "tier": "free"}, "client_id"),
        ({"client_id": "x" * 65, "tier": "free"}, "client_id"),
        ({"client_id": "bad id!", "tier": "free"}, "client_id"),
        ({"client_id": "../x", "tier": "free"}, "client_id"),
        ({"client_id": "ok", "tier": "gold"}, "tier"),
        ({"client_id": "ok"}, "tier"),
    ],
)
def test_invalid_input_is_rejected_before_the_limiter(client, app, payload, field):
    before = dict(app.state.limiter.clients)
    response = client.post(URL, json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["category"] == "invalid_input"
    assert field in error["fields"]
    assert app.state.limiter.clients == before
