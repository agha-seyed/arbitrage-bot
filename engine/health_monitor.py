import redis.asyncio as redis
import os
from loguru import logger
from datetime import datetime, timezone

class AccountHealthMonitor:
    """
    سیستم امتیازدهی سلامت اکانت در هر بوکمیکر
    ذخیرهسازی در Redis با key: health:{bookmaker_name}
    """
    def __init__(self, redis_client):
        self.r = redis_client

    async def get_win_rate(self, bookmaker: str, days: int = 7) -> float:
        """Mock method for win rate, since we don't have bet outcomes yet"""
        return 0.5  # Default 50%

    async def get_daily_bet_count(self, bookmaker: str) -> int:
        """گرفتن تعداد شرط‌های امروز"""
        key = f"bets:{datetime.now(timezone.utc):%Y-%m-%d}:{bookmaker.lower()}"
        return int(await self.r.get(key) or 0)
        
    async def increment_daily_bet_count(self, bookmaker: str):
        key = f"bets:{datetime.now(timezone.utc):%Y-%m-%d}:{bookmaker.lower()}"
        await self.r.incr(key)
        await self.r.expire(key, 86400)

    async def detect_max_stake_reduction(self, bookmaker: str) -> bool:
        """بررسی اینکه آیا بوکی لیمیت اعمال کرده یا نه"""
        return await self.r.get(f"stake_reduction:{bookmaker.lower()}") is not None

    async def detect_timing_pattern(self, bookmaker: str) -> bool:
        """Mock method: always betting at exact same time"""
        return False

    async def calculate_health_score(self, bookmaker: str) -> int:
        """
        امتیاز از 0 تا 100:
        - 80-100: سبز — اکانت سالم
        - 50-79: زرد — احتیاط
        - 0-49: قرمز — توقف فوری
        """
        score = 100
        
        # 1. Win Rate
        win_rate = await self.get_win_rate(bookmaker, days=7)
        if win_rate > 0.80:
            score -= 30
        elif win_rate > 0.65:
            score -= 15
        
        # 2. Daily bets
        daily_bets = await self.get_daily_bet_count(bookmaker)
        if daily_bets > 20:
            score -= 20
        elif daily_bets > 12:
            score -= 10
        
        # 3. Max stake reduction (limitation)
        if await self.detect_max_stake_reduction(bookmaker):
            score -= 40
        
        # 4. Timing pattern
        if await self.detect_timing_pattern(bookmaker):
            score -= 15
            
        score = max(0, score)
        await self.r.set(f"health:{bookmaker.lower()}", score)
        return score
