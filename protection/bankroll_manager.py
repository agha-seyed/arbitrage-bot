import redis.asyncio as aioredis
import structlog
from config import settings

log = structlog.get_logger()

class BankrollManager:
    """
    مدیریت بانک‌رول و سودها/ضررها
    """
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.base_bankroll = settings.TOTAL_BANKROLL_EUR
        
    async def get_current_bankroll(self) -> float:
        # در اینجا می‌توانیم سود و زیان‌های قطعی شده را از ردیس بخوانیم
        # فعلاً همان بیس را برمی‌گردانیم
        val = await self.redis.get("current_bankroll")
        if val:
            return float(val)
        return self.base_bankroll
