import redis.asyncio as aioredis
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()

class ExposureController:
    """
    کنترل سقف ریسک روزانه و کلی در هر بوکمیکر.
    """
    def __init__(self, redis_client: aioredis.Redis, max_daily: float = 3000.0):
        self.redis = redis_client
        self.max_daily = max_daily
        
    async def can_place(self, bookmaker: str, stake: float) -> bool:
        key = f"exp:{datetime.now(timezone.utc):%Y-%m-%d}:{bookmaker.lower()}"
        current = float(await self.redis.get(key) or 0)
        
        if current + stake > self.max_daily:
            log.warning("daily_exposure_limit_reached", bookmaker=bookmaker, current=current, stake=stake)
            return False
            
        # We don't increment here, increment happens when we ACTUALLY place/send the signal
        return True
        
    async def record_placement(self, bookmaker: str, stake: float):
        key = f"exp:{datetime.now(timezone.utc):%Y-%m-%d}:{bookmaker.lower()}"
        await self.redis.incrbyfloat(key, stake)
        await self.redis.expire(key, 86400)
