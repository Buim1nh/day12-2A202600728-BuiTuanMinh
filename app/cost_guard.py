import time
import json
import logging
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger(__name__)

_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

def check_and_record_cost(user_id: str, input_tokens: int, output_tokens: int, redis_client=None):
    global _daily_cost, _cost_reset_day
    
    # Pricing per 1k tokens
    cost = (input_tokens / 1000) * 0.00015 + (output_tokens / 1000) * 0.0006
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    if redis_client is None:
        today = time.strftime("%Y-%m-%d")
        if today != _cost_reset_day:
            _daily_cost = 0.0
            _cost_reset_day = today
        if _daily_cost + cost > settings.daily_budget_usd:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Daily budget exceeded",
                    "used_usd": round(_daily_cost, 6),
                    "budget_usd": settings.daily_budget_usd,
                }
            )
        _daily_cost += cost
        return

    key = f"cost:{user_id}:{current_month}"
    try:
        current_spent_str = redis_client.get(key)
        current_spent = float(current_spent_str) if current_spent_str else 0.0
        
        if current_spent + cost > settings.monthly_budget_usd:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(current_spent, 6),
                    "budget_usd": settings.monthly_budget_usd,
                }
            )
        
        if cost > 0:
            redis_client.incrbyfloat(key, cost)
            redis_client.expire(key, 35 * 24 * 3600)
    except Exception as e:
        logger.error(json.dumps({"event": "cost_guard_redis_error", "error": str(e)}))
        # Fallback to in-memory daily check
        today = time.strftime("%Y-%m-%d")
        if today != _cost_reset_day:
            _daily_cost = 0.0
            _cost_reset_day = today
        if _daily_cost + cost > settings.daily_budget_usd:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Daily budget exceeded",
                    "used_usd": round(_daily_cost, 6),
                    "budget_usd": settings.daily_budget_usd,
                }
            )
        _daily_cost += cost
