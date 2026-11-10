"""Non-Gemini API responses under 200 ms (plan performance goal; task T054)."""

import time

import pytest

PATHS = [
    "/api/health",
    "/api/part-1a/tiers",
    "/api/part-1a/harness",
    "/api/part-1b/evaluation",
    "/api/part-1b/evaluation/history",
    "/api/evidence",
    "/api/evidence/1b-dataset",
]


@pytest.mark.parametrize("path", PATHS)
def test_endpoint_responds_within_200_ms(client, path):
    client.get(path)  # warm-up
    for _ in range(20):
        started = time.perf_counter()
        response = client.get(path)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert response.status_code == 200
        assert elapsed_ms < 200, f"{path} took {elapsed_ms:.1f} ms"


def test_rate_limit_request_within_200_ms(client):
    for index in range(20):
        started = time.perf_counter()
        client.post("/api/part-1a/request", json={"client_id": f"perf-{index}", "tier": "free"})
        assert (time.perf_counter() - started) * 1000 < 200
