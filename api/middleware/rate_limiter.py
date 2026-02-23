"""
ReconX Rate Limiter
Token bucket algorithm for API rate limiting
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class Bucket:
    tokens: float
    last_update: float
    rate: float  # tokens per second
    capacity: float

class RateLimiter:
    def __init__(self):
        self.buckets: Dict[str, Bucket] = {}
        self.default_rate = 10  # 10 requests per second
        self.default_capacity = 20  # burst capacity
    
    def _get_bucket(self, key: str, rate: Optional[float] = None, 
                    capacity: Optional[float] = None) -> Bucket:
        """Get or create token bucket for key"""
        if key not in self.buckets:
            self.buckets[key] = Bucket(
                tokens=capacity or self.default_capacity,
                last_update=time.time(),
                rate=rate or self.default_rate,
                capacity=capacity or self.default_capacity
            )
        return self.buckets[key]
    
    def is_allowed(self, key: str, tokens: float = 1) -> bool:
        """Check if request is allowed"""
        bucket = self._get_bucket(key)
        now = time.time()
        
        # Add tokens based on time passed
        elapsed = now - bucket.last_update
        bucket.tokens = min(
            bucket.capacity,
            bucket.tokens + elapsed * bucket.rate
        )
        bucket.last_update = now
        
        # Check if enough tokens
        if bucket.tokens >= tokens:
            bucket.tokens -= tokens
            return True
        
        return False
    
    def get_wait_time(self, key: str, tokens: float = 1) -> float:
        """Get time to wait before request is allowed"""
        bucket = self._get_bucket(key)
        
        if bucket.tokens >= tokens:
            return 0
        
        needed = tokens - bucket.tokens
        return needed / bucket.rate

class ScanRateLimiter:
    """Rate limiter for external scanning tools"""
    def __init__(self):
        self.target_limits: Dict[str, float] = {}
        self.last_request: Dict[str, float] = {}
        self.default_delay = 1.0  # seconds between requests
    
    def set_limit(self, target: str, requests_per_second: float):
        """Set rate limit for target"""
        self.target_limits[target] = 1.0 / requests_per_second
    
    async def acquire(self, target: str):
        """Wait if necessary to respect rate limit"""
        import asyncio
        
        delay = self.target_limits.get(target, self.default_delay)
        now = time.time()
        
        if target in self.last_request:
            elapsed = now - self.last_request[target]
            if elapsed < delay:
                wait = delay - elapsed
                await asyncio.sleep(wait)
        
        self.last_request[target] = time.time()
    
    def adapt_to_response(self, target: str, status_code: int):
        """Adapt rate based on response (backoff on 429)"""
        if status_code == 429:  # Too Many Requests
            current = self.target_limits.get(target, self.default_delay)
            self.target_limits[target] = current * 2  # Double delay
        elif status_code == 200:
            # Slowly restore normal rate
            current = self.target_limits.get(target, self.default_delay)
            self.target_limits[target] = max(self.default_delay, current * 0.9)
