import asyncio
import aiohttp
import redis.asyncio as aioredis
from datetime import datetime, timedelta, timezone

from core.odds_fetcher import OddsFetcher
from filters.odds_verifier import OddsVerifier
from filters.profit_filter import DynamicProfitFilter
from filters.bookmaker_classifier import BookmakerClassifier
from filters.steam_detector import SteamDetector
from filters.pipeline import FilterPipeline
from protection.account_health import AccountHealthMonitor
from protection.exposure_control import ExposureController
from config import settings

async def test():
    redis_client = aioredis.from_url(settings.REDIS_URL)
    
    async with aiohttp.ClientSession() as session:
        fetcher = OddsFetcher(session)
        
        pipeline = FilterPipeline(
            verifier=OddsVerifier(fetcher),
            profit_filter=DynamicProfitFilter(),
            classifier=BookmakerClassifier(),
            steam_detector=SteamDetector(redis_client),
            health_monitor=AccountHealthMonitor(redis_client),
            exposure_controller=ExposureController(redis_client)
        )
        
        # یک opportunity ساختگی با همه فیلدها
        test_opp = {
            "event_id": "test_123",
            "sport_key": "soccer_italy_serie_a",
            "event_name": "Inter vs Milan",
            "profit_pct": 2.5,
            "commence_time": (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat(),
            "legs": [
                {
                    "bookmaker": "snai",
                    "market": "h2h",
                    "outcome": "Inter",
                    "odd": 2.10,
                    "stake": 50.0
                },
                {
                    "bookmaker": "eurobet",
                    "market": "h2h",
                    "outcome": "Milan",
                    "odd": 3.20,
                    "stake": 32.0
                }
            ]
        }
        
        approved, result = await pipeline.run(test_opp)
        print(f"\n{'✅ تایید شد' if approved else '❌ رد شد'}: {result}")
        
        if approved:
            print(f"  کیفیت: {result['quality']['quality']} {result['quality']['emoji']}")
            print(f"  فوریت: {result['urgency']['emoji']} {result['urgency']['label']}")
    
    await redis_client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
