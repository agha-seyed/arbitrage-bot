import redis.asyncio as aioredis
from datetime import datetime, timezone
import structlog
import uuid

log = structlog.get_logger()

class CLVTracker:
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        
    def record_placement(self, opportunity: dict):
        """
        ثبت یک شرط (فایرو اند فورگت از طرف main)
        البته این تابع چون I/O در redis می‌خواهد معمولا async باید باشد.
        اما در کدی که یوزر داد (clv_tracker.record_placement) بدون await استفاده شده است.
        پس بهتر است با create_task آن را اجرا کنیم.
        """
        import asyncio
        asyncio.create_task(self._record_async(opportunity))
        
    async def _record_async(self, opportunity: dict):
        event_id = opportunity.get('event_id', 'unknown')
        sport_key = opportunity.get('sport_key', 'unknown')
        
        for leg in opportunity['legs']:
            bet_id = f"{event_id}_{uuid.uuid4().hex[:6]}"
            key = f"bet:{bet_id}"
            data = {
                "event_id": event_id,
                "sport_key": sport_key,
                "bookmaker": leg['bookmaker'],
                "market": leg['market'],
                "outcome": leg['outcome'],
                "odd_taken": leg['odd'],
                "placed_at": datetime.now(timezone.utc).isoformat()
            }
            await self.redis.hset(key, mapping=data)
            # نگه داشتن برای حداکثر یک ماه
            await self.redis.expire(key, 86400 * 30)
        
        log.info("clv_tracked", event_id=event_id)

    async def get_average_clv(self, days: int = 30) -> float:
        """
        محاسبه میانگین CLV برای داشبورد.
        فعلاً به صورت پیش‌فرض 0 برمی‌گرداند تا زمانی که الگوریتم واقعی پیاده‌سازی شود.
        """
        return 0.0
