import pytest
from fastapi import HTTPException
from src.limiter import RateLimiter
import src.limiter as limiter_module

def test_ac1_ac2_limits_and_rejection():
    limiter = RateLimiter()
    # AC1: Requests within the limit return successfully
    for _ in range(5):
        assert limiter.check_request("client_1", "free") == True
    
    # AC2: Requests exceeding the limit are rejected with HTTP 429
    with pytest.raises(HTTPException) as excinfo:
        limiter.check_request("client_1", "free")
    assert excinfo.value.status_code == 429

def test_ac3_retry_headers():
    limiter = RateLimiter()
    for _ in range(5):
        limiter.check_request("client_2", "free")
    
    # AC3: HTTP 429 responses must include an appropriate rate-limit retry header
    with pytest.raises(HTTPException) as excinfo:
        limiter.check_request("client_2", "free")
    
    assert excinfo.value.headers is not None, "Headers missing from 429 response"
    assert "Retry-After" in excinfo.value.headers, "Retry-After header missing"

def test_ac4_client_isolation():
    limiter = RateLimiter()
    for _ in range(5):
        limiter.check_request("client_3", "free")
    
    # AC4: The system must isolate limits correctly based on client ID
    assert limiter.check_request("client_4", "free") == True


# ---------------------------------------------------------------------------
# Tests added 2026-11-07 (change cycle: Part-1A/change-cycles/2026-11-07-ac3-retry-after).
# Derived from speckit.specify.md: Client Tiers, AC1, AC2 and the clarified AC3.
# A fake clock replaces the limiter's time source so timing is deterministic.
# ---------------------------------------------------------------------------

# Requests per minute for each tier, as stated in speckit.specify.md (Client Tiers).
SPEC_TIER_LIMITS = {"free": 5, "standard": 20, "premium": 100}


class FakeClock:
    """Stands in for the `time` module used by src/limiter.py."""

    def __init__(self, start=1_000.0):
        self.now = start

    def time(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(limiter_module, "time", fake)
    return fake


def _send_until_rejected(limiter, client_id, tier, clock, gap):
    """Send requests `gap` seconds apart until one is rejected; return that exception."""
    for _ in range(10 * SPEC_TIER_LIMITS[tier]):
        try:
            limiter.check_request(client_id, tier)
        except HTTPException as exc:
            return exc
        clock.advance(gap)
    pytest.fail("The bucket was never exhausted.")


@pytest.mark.parametrize("tier", ["free", "standard", "premium"])
def test_ac1_ac2_spec_capacity_per_tier(tier, clock):
    # AC1: a fresh client may send the tier's full per-minute allowance immediately.
    limiter = RateLimiter()
    for _ in range(SPEC_TIER_LIMITS[tier]):
        assert limiter.check_request(f"capacity-{tier}", tier) is True

    # AC2: the next immediate request is rejected with HTTP 429.
    with pytest.raises(HTTPException) as excinfo:
        limiter.check_request(f"capacity-{tier}", tier)
    assert excinfo.value.status_code == 429


@pytest.mark.parametrize("gap", [0.0, 0.01, 0.25])
@pytest.mark.parametrize("tier", ["free", "standard", "premium"])
def test_ac3_retry_after_is_smallest_sufficient_wait(tier, gap, clock):
    limiter = RateLimiter()
    rejection = _send_until_rejected(limiter, "retry-client", tier, clock, gap)

    retry_after = rejection.headers["Retry-After"]
    assert retry_after.isdigit() and int(retry_after) >= 1, (
        f"Retry-After must be a positive whole number of seconds, got {retry_after!r}"
    )
    wait = int(retry_after)

    if wait > 1:
        # One second earlier than advertised is still too early.
        clock.advance(wait - 1)
        with pytest.raises(HTTPException):
            limiter.check_request("retry-client", tier)
        clock.advance(1)
    else:
        clock.advance(wait)

    # A client that waits exactly the advertised time must be accepted.
    try:
        accepted = limiter.check_request("retry-client", tier)
    except HTTPException as exc:
        pytest.fail(
            f"Expected acceptance after waiting the advertised Retry-After of {wait}s "
            f"({tier} tier, {gap}s between requests); observed HTTP {exc.status_code} "
            f"with a new Retry-After of {exc.headers.get('Retry-After')}s."
        )
    assert accepted is True
