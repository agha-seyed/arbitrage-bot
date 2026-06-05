import redis.asyncio as redis
from loguru import logger
from datetime import datetime, timezone
import uuid

class CLVTracker:
    """
    Closing Line Value Tracker
    CLV مثبت = شما بهتر از بازار شرط بستید
    CLV منفی = شما بدتر از بازار شرط بستید
    """
    def __init__(self, redis_client):
        self.r = redis_client
        
    async def record_bet_placement(self, odd_taken: float, event_id: str, market: str, bookmaker: str) -> str:
        """ضبط شرط در زمان ثبت"""
        bet_id = str(uuid.uuid4())
        key = f"bet:{bet_id}"
        
        await self.r.hmset(key, {
            'odd_taken': odd_taken,
            'event_id': event_id,
            'market': market,
            'bookmaker': bookmaker,
            'placed_at': datetime.now(timezone.utc).isoformat()
        })
        await self.r.expire(key, 86400 * 7)  # 7 days retention
        
        logger.info(f"CLV Tracker: شرط ثبت شد {bet_id} با ضریب {odd_taken}")
        return bet_id
    
    async def calculate_clv(self, bet_id: str, closing_odd: float) -> float | None:
        """محاسبه CLV بعد از بسته شدن بازار"""
        key = f"bet:{bet_id}"
        bet_data = await self.r.hgetall(key)
        
        if not bet_data or 'odd_taken' not in bet_data:
            return None
            
        odd_taken = float(bet_data['odd_taken'])
        if closing_odd <= 0:
            return None
            
        clv = (odd_taken / closing_odd - 1) * 100
        await self.r.hset(key, 'clv', clv)
        logger.info(f"CLV محاسبه شد برای {bet_id}: {clv:.2f}%")
        
        # Add to historical CLV list
        bookmaker = bet_data.get('bookmaker', 'unknown')
        await self.r.lpush(f"clv_history:{bookmaker}", clv)
        await self.r.ltrim(f"clv_history:{bookmaker}", 0, 99) # Keep last 100
        
        return clv
