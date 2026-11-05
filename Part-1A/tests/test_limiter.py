import pytest
from fastapi import HTTPException
from src.limiter import RateLimiter

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
