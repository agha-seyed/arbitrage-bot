import json
import time
import redis.asyncio as aioredis
from config import settings
import structlog

log = structlog.get_logger()

class SteamDetector:
    
    WINDOW_SECONDS = 30       # پنجره زمانی بررسی
    STEAM_THRESHOLD = 0.05    # 5% تغییر = steam
    HISTORY_SIZE = 100        # حداکثر تعداد تغییرات ذخیره شده
    TTL_SECONDS = 3600        # بعد از 1 ساعت داده قدیمی پاک می‌شود
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    def _key(self, event_id: str, bookmaker: str, market: str) -> str:
        return f"steam:{event_id}:{bookmaker}:{market}"
    
    async def record_odd(self, event_id: str, bookmaker: str, market: str, odd: float):
        """
        این تابع باید در حلقه اصلی اسکن، برای هر ضریب فراخوانی شود.
        قبل از محاسبه آربیتراژ — نه بعد از آن.
        """
        key = self._key(event_id, bookmaker, market)
        entry = json.dumps({"odd": odd, "ts": time.time()})
        
        pipe = self.redis.pipeline()
        pipe.lpush(key, entry)
        pipe.ltrim(key, 0, self.HISTORY_SIZE - 1)
        pipe.expire(key, self.TTL_SECONDS)
        await pipe.execute()
    
    async def is_steaming(self, event_id: str, bookmaker: str, market: str) -> bool:
        """
        بررسی می‌کند که آیا در ۳۰ ثانیه اخیر تغییر ناگهانی بوده یا نه.
        True = steam تشخیص داده شد = این آربیتراژ خطرناک است
        """
        key = self._key(event_id, bookmaker, market)
        raw_history = await self.redis.lrange(key, 0, -1)
        
        if len(raw_history) < 2:
            return False
        
        history = [json.loads(x) for x in raw_history]
        now = time.time()
        
        # فقط رکوردهای ۳۰ ثانیه اخیر
        recent = [h for h in history if now - h['ts'] <= self.WINDOW_SECONDS]
        
        if len(recent) < 2:
            return False
        
        newest_odd = recent[0]['odd']
        oldest_odd = recent[-1]['odd']
        
        if oldest_odd == 0:
            return False
        
        change_pct = abs(newest_odd - oldest_odd) / oldest_odd
        
        if change_pct >= self.STEAM_THRESHOLD:
            log.warning(
                "steam_detected",
                event_id=event_id,
                bookmaker=bookmaker,
                market=market,
                change_pct=round(change_pct * 100, 2),
                oldest_odd=oldest_odd,
                newest_odd=newest_odd
            )
            return True
        
        return False
