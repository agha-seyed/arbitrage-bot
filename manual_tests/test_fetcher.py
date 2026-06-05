import asyncio
import aiohttp
from core.odds_fetcher import OddsFetcher
from config import settings

async def test():
    async with aiohttp.ClientSession() as session:
        fetcher = OddsFetcher(session)
        data = await fetcher.get_odds("soccer_italy_serie_a", "h2h")
        
        if data is None:
            print("❌ fetcher برنگرداند — API key را چک کن")
            return
        
        print(f"✅ {len(data)} بازی دریافت شد")
        
        # چک کردن ساختار داده
        if data:
            event = data[0]
            assert 'id' in event, "❌ فیلد id وجود ندارد"
            assert 'bookmakers' in event, "❌ فیلد bookmakers وجود ندارد"
            assert 'commence_time' in event, "❌ فیلد commence_time وجود ندارد"
            print(f"✅ ساختار داده درست است")
            print(f"   نمونه: {event['home_team']} vs {event['away_team']}")

if __name__ == "__main__":
    asyncio.run(test())
