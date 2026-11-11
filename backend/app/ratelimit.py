"""Simple per-IP sliding-window limiter. In-memory, so it is per process; use Redis if you scale out.
Behind a proxy, uvicorn --proxy-headers makes request.client the real visitor IP."""
import collections, threading, time
from fastapi import HTTPException, Request
from .config import settings

_hits = collections.defaultdict(collections.deque)
_lock = threading.Lock()

def limit(max_calls: int, window_s: int, scope: str):
    def dep(request: Request):
        if not settings.rate_limit:
            return
        key = (scope, request.client.host if request.client else "unknown")
        now = time.monotonic()
        with _lock:
            q = _hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= max_calls:
                raise HTTPException(429, "Too many requests. Please wait a moment and try again.")
            q.append(now)
    return dep
