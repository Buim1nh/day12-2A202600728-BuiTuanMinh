import time
import json
import logging
from collections import defaultdict, deque
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

_rate_windows = defaultdict(deque)

def check_rate_limit(user_id: str, redis_client=None):
    if redis_client is None:
        # Fallback to in-memory
        now = time.time()
        window = _rate_windows[user_id]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return

    now = time.time()
    key = f"rate_limit:{user_id}"
    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - 60)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 60)
        _, request_count, _, _ = pipe.execute()
        if request_count > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
    except Exception as e:
        logger.error(json.dumps({"event": "rate_limiter_redis_error", "error": str(e)}))
        # Fallback to in-memory
        now = time.time()
        window = _rate_windows[user_id]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
        window.append(now)
