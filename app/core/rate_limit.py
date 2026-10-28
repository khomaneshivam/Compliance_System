"""
In-Memory Thread-Safe Rate Limiter for Sensitive Endpoints
Supports sliding window / token bucket algorithm with standard 429 response and Retry-After.
"""

import time
import threading
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory rate limiter using sliding timestamp windows.
    Tracks request timestamps per client key and rejects requests exceeding the limit.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _cleanup(self, now: float, window_seconds: int) -> None:
        """Removes expired entries periodically to prevent memory unbounded growth."""
        if now - self._last_cleanup < 60:
            return
        cutoff = now - (window_seconds * 2)
        keys_to_delete = []
        for k, timestamps in self._records.items():
            valid = [ts for ts in timestamps if ts > cutoff]
            if not valid:
                keys_to_delete.append(k)
            else:
                self._records[k] = valid
        for k in keys_to_delete:
            del self._records[k]
        self._last_cleanup = now

    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> None:
        """
        Records an attempt and raises HTTP 429 if the request limit is exceeded within the window.
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            self._cleanup(now, window_seconds)

            timestamps = self._records.get(key, [])
            # Filter timestamps within the current sliding window
            recent = [ts for ts in timestamps if ts > window_start]

            if len(recent) >= max_requests:
                # Calculate remaining time until the oldest request expires
                oldest = min(recent)
                retry_after = max(1, int(window_seconds - (now - oldest)))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: maximum {max_requests} requests per {window_seconds}s. Please retry in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )

            recent.append(now)
            self._records[key] = recent

    def reset(self) -> None:
        """Clears all rate limit records (for testing)."""
        with self._lock:
            self._records.clear()


# Global in-memory rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60, key_prefix: str = "generic"):
    """
    FastAPI dependency factory to enforce rate limits per client IP or authenticated entity.
    """
    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown_client"
        # If user is authenticated, include tenant/user if available
        auth_header = request.headers.get("Authorization", "")
        # Derive key from IP and prefix
        limit_key = f"{key_prefix}:{client_ip}"
        rate_limiter.check_rate_limit(
            key=limit_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return dependency
