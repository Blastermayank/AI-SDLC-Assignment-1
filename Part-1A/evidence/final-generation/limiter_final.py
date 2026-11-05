import time
from fastapi import HTTPException

TIERS = {
    "free": {"capacity": 5, "refill_rate": 5 / 60.0},
    "standard": {"capacity": 20, "refill_rate": 20 / 60.0},
    "premium": {"capacity": 100, "refill_rate": 100 / 60.0},
}

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        
        # Refill tokens based on time elapsed
        self.tokens += elapsed * self.refill_rate
        self.tokens = min(self.tokens, self.capacity)
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
        
    def time_until_next_token(self) -> int:
        if self.tokens >= 1:
            return 0
        return int(max(1, (1 - self.tokens) / self.refill_rate))

class RateLimiter:
    def __init__(self):
        self.clients: dict[str, TokenBucket] = {}

    def check_request(self, client_id: str, tier: str = "free"):
        if client_id not in self.clients:
            if tier not in TIERS:
                tier = "free"
            config = TIERS[tier]
            self.clients[client_id] = TokenBucket(config["capacity"], config["refill_rate"])
        
        bucket = self.clients[client_id]
        if not bucket.consume(1):
            retry_after = str(bucket.time_until_next_token())
            raise HTTPException(
                status_code=429, 
                detail="Too Many Requests",
                headers={"Retry-After": retry_after}
            )
        return True
