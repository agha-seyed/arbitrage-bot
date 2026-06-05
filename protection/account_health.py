import redis.asyncio as aioredis
import json
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()

class AccountHealthMonitor:
    
    SCORE_KEY = "health:score:{bookmaker}"
    HISTORY_KEY = "health:history:{bookmaker}"
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    async def calculate_and_store(self, bookmaker: str) -> int:
        """امتیاز را محاسبه کن و در Redis ذخیره کن"""
        score = await self._calculate_score(bookmaker)
        
        key = self.SCORE_KEY.format(bookmaker=bookmaker)
        await self.redis.set(key, score, ex=300)   # 5 دقیقه cache
        
        # اگر امتیاز کم شد، لاگ کن
        if score < 50:
            log.warning("account_health_critical", bookmaker=bookmaker, score=score)
        elif score < 70:
            log.info("account_health_warning", bookmaker=bookmaker, score=score)
        
        return score
    
    async def get_score(self, bookmaker: str) -> int:
        """امتیاز کش‌شده را بخوان"""
        key = self.SCORE_KEY.format(bookmaker=bookmaker)
        val = await self.redis.get(key)
        if val is None:
            return await self.calculate_and_store(bookmaker)
        return int(val)
    
    async def get_all_scores(self) -> dict:
        """
        امتیاز تمام بوکمیکرها را برای نمایش در داشبورد برمی‌گرداند.
        داشبورد این تابع را هر ۶۰ ثانیه فراخوانی می‌کند.
        """
        from filters.bookmaker_classifier import BookmakerClassifier
        classifier = BookmakerClassifier()
        all_books = list(classifier.SOFT)
        
        scores = {}
        for book in all_books:
            score = await self.get_score(book)
            scores[book] = {
                "score": score,
                "status": self._score_to_status(score),
                "color": self._score_to_color(score)
            }
        return scores
    
    def _score_to_status(self, score: int) -> str:
        if score >= 80:  return "HEALTHY"
        if score >= 50:  return "CAUTION"
        return "CRITICAL"
    
    def _score_to_color(self, score: int) -> str:
        if score >= 80:  return "#1D9E75"   # سبز
        if score >= 50:  return "#BA7517"   # زرد
        return "#E24B4A"                     # قرمز
    
    async def _calculate_score(self, bookmaker: str) -> int:
        score = 100
        
        # ۱. Win Rate این هفته
        win_rate = await self._get_win_rate(bookmaker, days=7)
        if win_rate > 0.80:   score -= 30
        elif win_rate > 0.65: score -= 15
        
        # ۲. تعداد شرط در ۲۴ ساعت
        daily_bets = await self._get_daily_bet_count(bookmaker)
        if daily_bets > 20:   score -= 20
        elif daily_bets > 12: score -= 10
        
        # ۳. محدودیت حداکثر شرط (باید دستی ثبت شود)
        if await self._is_stake_reduced(bookmaker):
            score -= 40
        
        return max(0, min(100, score))
    
    async def _get_win_rate(self, bookmaker: str, days: int) -> float:
        key = f"stats:wins:{bookmaker}"
        wins = int(await self.redis.get(f"{key}:wins") or 0)
        total = int(await self.redis.get(f"{key}:total") or 1)
        return wins / total if total > 0 else 0.0
    
    async def _get_daily_bet_count(self, bookmaker: str) -> int:
        key = f"daily:bets:{bookmaker}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        val = await self.redis.get(key)
        return int(val) if val else 0
    
    async def _is_stake_reduced(self, bookmaker: str) -> bool:
        return await self.redis.exists(f"stake_reduction:{bookmaker}") > 0
    
    async def mark_stake_reduced(self, bookmaker: str):
        """
        این تابع را دستی فراخوانی کن وقتی متوجه شدی بوکمیکر حداکثر شرطت را کم کرده.
        مثال: await health.mark_stake_reduced('snai')
        """
        key = f"stake_reduction:{bookmaker}"
        await self.redis.set(key, "1", ex=86400 * 7)   # 7 روز
        log.warning("stake_reduction_flagged", bookmaker=bookmaker)
