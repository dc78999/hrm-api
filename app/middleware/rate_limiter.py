import time
import json
import logging
import hashlib
import threading
import os
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

class InMemoryRateLimiter:
    """Thread-safe in-memory rate limiter with sliding window algorithm"""
    
    def __init__(self, persistence_file: Optional[str] = None):
        self._store = defaultdict(deque)  # key -> deque of timestamps
        self._lock = threading.RLock()
        self._persistence_file = persistence_file
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Clean up every 5 minutes
        
        # Load persisted data if available
        self._load_from_file()
    
    def _load_from_file(self):
        """Load rate limit data from persistence file"""
        if not self._persistence_file or not os.path.exists(self._persistence_file):
            return
        
        try:
            with open(self._persistence_file, 'r') as f:
                data = json.load(f)
                current_time = time.time()
                
                # Only load recent entries (within last hour)
                with self._lock:
                    for key, timestamps in data.items():
                        recent_timestamps = [ts for ts in timestamps if current_time - ts < 3600]
                        if recent_timestamps:
                            self._store[key] = deque(recent_timestamps)
            
            logger.info(f"Loaded rate limit data from {self._persistence_file}")
        except Exception as e:
            logger.error(f"Failed to load rate limit data: {e}")
    
    def _save_to_file(self):
        """Save current rate limit data to persistence file"""
        if not self._persistence_file:
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._persistence_file), exist_ok=True)
            
            with self._lock:
                # Convert deques to lists for JSON serialization
                data = {key: list(timestamps) for key, timestamps in self._store.items() if timestamps}
            
            with open(self._persistence_file, 'w') as f:
                json.dump(data, f)
            
        except Exception as e:
            logger.error(f"Failed to save rate limit data: {e}")
    
    def _cleanup_old_entries(self):
        """Remove old entries from memory to prevent memory leaks"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        with self._lock:
            keys_to_remove = []
            for key, timestamps in self._store.items():
                # Remove timestamps older than 1 hour
                while timestamps and current_time - timestamps[0] > 3600:
                    timestamps.popleft()
                
                # Mark empty deques for removal
                if not timestamps:
                    keys_to_remove.append(key)
            
            # Remove empty entries
            for key in keys_to_remove:
                del self._store[key]
        
        self._last_cleanup = current_time
        
        # Save to file periodically
        if self._persistence_file:
            self._save_to_file()
    
    def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> Dict[str, Any]:
        """Check rate limit using sliding window algorithm"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        with self._lock:
            timestamps = self._store[key]
            
            # Remove expired entries
            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()
            
            current_count = len(timestamps)
            
            if current_count < limit:
                timestamps.append(current_time)
                allowed = True
                remaining = limit - current_count - 1
                # Update current_count after adding the new timestamp
                current_count = len(timestamps)
            else:
                allowed = False
                remaining = 0
            
            # Calculate reset time (when the oldest entry will expire)
            reset_time = int(timestamps[0] + window_seconds) if timestamps else int(current_time + window_seconds)
            
            result = {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time,
                "retry_after": window_seconds if not allowed else None,
                "current_count": current_count
            }
        
        # Periodic cleanup
        self._cleanup_old_entries()
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the rate limiter"""
        with self._lock:
            total_keys = len(self._store)
            total_entries = sum(len(timestamps) for timestamps in self._store.values())
            
            return {
                "total_keys": total_keys,
                "total_entries": total_entries,
                "cleanup_interval": self._cleanup_interval,
                "last_cleanup": self._last_cleanup
            }
    
    def clear(self):
        """Clear all rate limit data"""
        with self._lock:
            self._store.clear()
        
        if self._persistence_file and os.path.exists(self._persistence_file):
            try:
                os.remove(self._persistence_file)
            except Exception as e:
                logger.error(f"Failed to remove persistence file: {e}")

class RateLimitRule:
    """Represents a rate limiting rule"""
    
    def __init__(self, max_requests: int, window_seconds: int, name: str = "default"):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.name = name
    
    def __repr__(self):
        return f"RateLimitRule({self.name}: {self.max_requests}/{self.window_seconds}s)"

class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, persistence_dir: Optional[str] = None):
        # Initialize persistence file path
        persistence_file = None
        if persistence_dir:
            os.makedirs(persistence_dir, exist_ok=True)
            persistence_file = os.path.join(persistence_dir, "rate_limits.json")
        
        self.limiter = InMemoryRateLimiter(persistence_file)
        
        # Define rate limiting rules
        self.rules = {
            # General API limits
            "api_general": RateLimitRule(10000, 3600, "api_general"),     # 1000/hour
            "api_burst": RateLimitRule(1000, 60, "api_burst"),           # 100/minute
            
            # Search endpoint specific limits
            "search_detailed": RateLimitRule(2000, 3600, "search_detailed"), # 200/hour
            "search_burst": RateLimitRule(200, 60, "search_burst"),          # 20/minute
            
            # Authentication endpoints (for future use)
            "auth": RateLimitRule(10, 300, "auth"),                     # 10/5min
            
            # Health check limits (very permissive)
            "health": RateLimitRule(1000, 60, "health"),               # 1000/minute
        }
        
        logger.info(f"Rate limiter initialized with {len(self.rules)} rules")
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return await call_next(request)
        
        # Get applicable rules for this request
        rules_to_check = self._get_applicable_rules(request)
        
        # Check each applicable rule
        rate_limit_info = None
        for rule_name, rule in rules_to_check.items():
            client_key = self._get_client_key(request, rule_name)
            
            current_info = self.limiter.check_rate_limit(
                key=client_key,
                limit=rule.max_requests,
                window_seconds=rule.window_seconds
            )
            
            # If any rule is violated, return rate limit error
            if not current_info["allowed"]:
                current_info["rule_name"] = rule_name
                return self._create_rate_limit_response(current_info)
            
            # Keep track of the most restrictive rule for headers
            if rate_limit_info is None or current_info["remaining"] < rate_limit_info["remaining"]:
                rate_limit_info = current_info
                rate_limit_info["rule_name"] = rule_name
        
        # Process request normally
        response = await call_next(request)
        
        # Add rate limiting headers to successful responses
        if rate_limit_info:
            self._add_rate_limit_headers(response, rate_limit_info)
        
        return response
    
    def _get_client_key(self, request: Request, rule_name: str) -> str:
        """Generate unique key for rate limiting"""
        client_ip = self._get_client_ip(request)
        org_id = request.headers.get("X-Organization-ID", "anonymous")
        user_agent = request.headers.get("User-Agent", "unknown")[:50]
        
        # Create composite key with rule name
        key_components = [rule_name, client_ip, org_id, hashlib.md5(user_agent.encode()).hexdigest()[:8]]
        return ":".join(key_components)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support"""
        # Check for forwarded headers (common in production behind load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped"""
        path = request.url.path
        
        # Skip for OpenAPI documentation and static assets
        skip_paths = ["/docs", "/openapi.json", "/redoc", "/favicon.ico"]
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_applicable_rules(self, request: Request) -> Dict[str, RateLimitRule]:
        """Determine which rate limiting rules apply to this request"""
        path = request.url.path
        rules_to_apply = {}
        
        # Health endpoints get their own lenient rules
        if path.startswith("/health"):
            rules_to_apply["health"] = self.rules["health"]
            return rules_to_apply
        
        # Apply general API limits to all API endpoints
        if path.startswith("/api/"):
            rules_to_apply["api_general"] = self.rules["api_general"]
            rules_to_apply["api_burst"] = self.rules["api_burst"]
        
        # Apply search-specific limits
        if "/search" in path:
            rules_to_apply["search_detailed"] = self.rules["search_detailed"]
            rules_to_apply["search_burst"] = self.rules["search_burst"]
        
        return rules_to_apply
    
    def _create_rate_limit_response(self, rate_limit_info: Dict[str, Any]) -> JSONResponse:
        """Create HTTP 429 response for rate limit exceeded"""
        headers = {
            "X-RateLimit-Limit": str(rate_limit_info["limit"]),
            "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
            "X-RateLimit-Reset": str(rate_limit_info["reset_time"]),
        }
        
        if rate_limit_info.get("retry_after"):
            headers["Retry-After"] = str(rate_limit_info["retry_after"])
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {rate_limit_info['limit']} requests per window.",
                "rule": rate_limit_info.get("rule_name", "unknown"),
                "retry_after": rate_limit_info.get("retry_after"),
                "reset_time": rate_limit_info["reset_time"]
            },
            headers=headers
        )
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_info: Dict[str, Any]):
        """Add rate limiting headers to response"""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset_time"])
        
        if rate_limit_info.get("rule_name"):
            response.headers["X-RateLimit-Rule"] = rate_limit_info["rule_name"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        limiter_stats = self.limiter.get_stats()
        
        return {
            "limiter": limiter_stats,
            "rules": {name: {"max_requests": rule.max_requests, "window_seconds": rule.window_seconds} 
                     for name, rule in self.rules.items()}
        }
    
    def clear_limits(self):
        """Clear all rate limits (useful for testing)"""
        self.limiter.clear()

# Decorator for additional rate limiting on specific endpoints
def rate_limit(max_requests: int, window_seconds: int, rule_name: str = None):
    """
    Decorator for endpoint-specific rate limiting
    Note: This is for future use with endpoint-specific limits
    """
    def decorator(func):
        # Store rate limit metadata on the function
        func._rate_limit = {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
            "rule_name": rule_name or func.__name__
        }
        return func
    return decorator
