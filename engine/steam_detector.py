import redis.asyncio as redis
from loguru import logger
import json
import time

class SteamDetector:
    """
    Steam (Sudden Market Movement) Detector
    تشخیص افت ناگهانی بیش از ۵ درصد در ۳۰ ثانیه
    """
    def __init__(self, redis_client):
        self.r = redis_client

    async def record_odd_snapshot(self, event_id: str, bookmaker: str, market: str, odd: float):
        """ثبت ضریب در Redis با timestamp"""
        key = f"odds_history:{event_id}:{bookmaker}:{market}"
        await self.r.lpush(key, json.dumps({
            'odd': odd, 
            'timestamp': time.time()
        }))
        await self.r.ltrim(key, 0, 49)   # فقط 50 تغییر آخر
        await self.r.expire(key, 3600)   # پاک شدن بعد از یک ساعت

    async def detect_steam(self, event_id: str, bookmaker: str, market: str, window_seconds: int = 30) -> bool:
        """
        بررسی اینکه آیا در 30 ثانیه اخیر تغییر ناگهانی بوده
        """
        key = f"odds_history:{event_id}:{bookmaker}:{market}"
        history_raw = await self.r.lrange(key, 0, -1)
        
        if not history_raw:
            return False
            
        history = [json.loads(x) for x in history_raw]
        now = time.time()
        
        # پیدا کردن رکوردهایی که مربوط به ۳۰ ثانیه گذشته هستند
        recent = [h for h in history if now - h['timestamp'] <= window_seconds]
        
        if len(recent) < 2:
            return False
            
        # جدیدترین در ایندکس 0 است، قدیمی‌ترین در ایندکس آخر
        oldest_odd = recent[-1]['odd']
        newest_odd = recent[0]['odd']
        
        if oldest_odd == 0:
            return False
            
        change_pct = abs(newest_odd - oldest_odd) / oldest_odd * 100
        
        if change_pct > 5.0:
            logger.warning(f"STEAM DETECTED: {event_id} {bookmaker} {market} changed {change_pct:.1f}%")
            return True
            
        return False
