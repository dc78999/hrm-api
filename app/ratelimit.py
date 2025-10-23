import time
import threading
from typing import Dict

class TokenBucket:
    def __init__(self, capacity: int, refill_rate_per_sec: float):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate_per_sec
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.timestamp
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.timestamp = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    def __init__(self, capacity: int = 100, refill_rate_per_sec: float = 1.0):
        # capacity = max burst, refill_rate = tokens added per second
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = threading.Lock()

    def allow_request(self, key: str) -> bool:
        with self.lock:
            if key not in self.buckets:
                self.buckets[key] = TokenBucket(self.capacity, self.refill_rate)
            bucket = self.buckets[key]
        return bucket.consume(1)
