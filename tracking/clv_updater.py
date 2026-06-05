"""
این اسکریپت هر شب ساعت ۲ بامداد اجرا می‌شود (cron: 0 2 * * *)
شرط‌هایی که دیروز ثبت شدند را پیدا می‌کند، ضریب بسته شدن را از API می‌گیرد،
CLV را محاسبه می‌کند و در Redis ذخیره می‌کند.
"""

import asyncio
import aiohttp
import redis.asyncio as aioredis
from datetime import datetime, timedelta, timezone
from config import settings
import structlog

log = structlog.get_logger()

class CLVUpdater:
    
    def __init__(self, redis_client: aioredis.Redis, session: aiohttp.ClientSession):
        self.redis = redis_client
        self.session = session
    
    async def run_daily_update(self):
        """اجرای روزانه: پردازش تمام شرط‌های دیروز"""
        bet_keys = await self.redis.keys("bet:*")
        
        processed = 0
        errors = 0
        
        for key in bet_keys:
            try:
                bet_data = await self.redis.hgetall(key)
                if not bet_data or bet_data.get(b'clv'):
                    continue   # قبلاً محاسبه شده
                
                # دریافت ضریب بسته شدن
                closing_odd = await self._get_closing_odd(
                    sport_key=bet_data[b'sport_key'].decode(),
                    event_id=bet_data[b'event_id'].decode(),
                    bookmaker=bet_data[b'bookmaker'].decode(),
                    market=bet_data[b'market'].decode(),
                    outcome=bet_data[b'outcome'].decode()
                )
                
                if closing_odd is None:
                    continue
                
                # محاسبه CLV
                odd_taken = float(bet_data[b'odd_taken'])
                clv = (odd_taken / closing_odd - 1) * 100
                
                await self.redis.hset(key, mapping={
                    'clv': round(clv, 4),
                    'closing_odd': closing_odd,
                    'clv_updated_at': datetime.now(timezone.utc).isoformat()
                })
                
                processed += 1
                log.info("clv_calculated", key=key.decode(), clv=clv, odd_taken=odd_taken, closing=closing_odd)
                
            except Exception as e:
                errors += 1
                log.error("clv_update_error", key=key, error=str(e))
        
        log.info("clv_update_complete", processed=processed, errors=errors)
        return {"processed": processed, "errors": errors}
    
    async def get_average_clv(self, days: int = 30) -> float:
        """
        میانگین CLV در N روز گذشته.
        CLV مثبت = شما بهتر از بازار شرط می‌بندید (خوب است).
        CLV منفی = استراتژی مشکل دارد.
        """
        bet_keys = await self.redis.keys("bet:*")
        clv_values = []
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        for key in bet_keys:
            data = await self.redis.hgetall(key)
            if not data or b'clv' not in data:
                continue
            
            placed_at_raw = data.get(b'placed_at', b'')
            try:
                placed_at_str = placed_at_raw.decode()
                if placed_at_str.endswith("Z"):
                    placed_at_str = placed_at_str[:-1] + "+00:00"
                placed_at = datetime.fromisoformat(placed_at_str)
                if placed_at.tzinfo is None:
                    placed_at = placed_at.replace(tzinfo=timezone.utc)
                if placed_at < cutoff:
                    continue
            except:
                continue
            
            clv_values.append(float(data[b'clv']))
        
        if not clv_values:
            return 0.0
        
        avg = sum(clv_values) / len(clv_values)
        log.info("clv_average", days=days, count=len(clv_values), average_clv=round(avg, 4))
        return avg
    
    async def _get_closing_odd(self, sport_key, event_id, bookmaker, market, outcome) -> float | None:
        """
        ضریب بسته شدن را از API دریافت کن.
        """
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds-history"
        params = {
            "apiKey": settings.ODDS_API_KEY,
            "regions": "eu",
            "markets": market,
            "eventIds": event_id,
            "oddsFormat": "decimal",
        }
        try:
            async with self.session.get(url, params=params) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                for event in data.get('data', []):
                    for bm in event.get('bookmakers', []):
                        if bm['key'] != bookmaker:
                            continue
                        for mkt in bm.get('markets', []):
                            if mkt['key'] != market:
                                continue
                            for out in mkt.get('outcomes', []):
                                if out['name'] == outcome:
                                    return float(out['price'])
        except Exception as e:
            log.error("closing_odd_fetch_error", error=str(e))
        return None

async def main():
    redis_client = aioredis.from_url(settings.REDIS_URL)
    async with aiohttp.ClientSession() as session:
        updater = CLVUpdater(redis_client, session)
        result = await updater.run_daily_update()
        print(f"CLV Update: {result}")
        
        avg = await updater.get_average_clv(days=30)
        print(f"Average CLV (30d): {avg:.2f}%")
    
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
