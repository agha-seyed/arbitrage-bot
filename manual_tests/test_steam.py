import asyncio
import redis.asyncio as aioredis
from filters.steam_detector import SteamDetector
from config import settings

async def test():
    redis_client = aioredis.from_url(settings.REDIS_URL)
    detector = SteamDetector(redis_client)
    
    # شبیهسازی تغییر ناگهانی ضریب
    event_id = "test_event_001"
    bookmaker = "snai"
    market = "h2h"
    
    # ثبت ضریب اولیه
    await detector.record_odd(event_id, bookmaker, market, 2.10)
    await asyncio.sleep(0.1)
    
    # ثبت ضریب بدون تغییر زیاد
    await detector.record_odd(event_id, bookmaker, market, 2.12)
    result = await detector.is_steaming(event_id, bookmaker, market)
    assert result == False, "❌ باید False برگرداند (تغییر کم)"
    print("✅ تغییر کم: steam تشخیص داده نشد (درست)")
    
    # ثبت ضریب با تغییر زیاد (بیش از 5%)
    await detector.record_odd(event_id, bookmaker, market, 1.85)
    result = await detector.is_steaming(event_id, bookmaker, market)
    assert result == True, "❌ باید True برگرداند (تغییر زیاد)"
    print("✅ تغییر زیاد: steam تشخیص داده شد (درست)")
    
    await redis_client.aclose()
    print("✅ SteamDetector درست کار میکند")

if __name__ == "__main__":
    asyncio.run(test())
