import asyncio
import aiohttp
from filters.odds_verifier import OddsVerifier
from core.odds_fetcher import OddsFetcher
from config import settings

async def test():
    async with aiohttp.ClientSession() as session:
        fetcher = OddsFetcher(session)
        verifier = OddsVerifier(fetcher)
        
        # ابتدا یک event_id واقعی بگیر
        data = await fetcher.get_odds("soccer_italy_serie_a", "h2h")
        if not data:
            print("⚠️ دادهای برای تست نیست")
            return
        
        event = data[0]
        bm = event['bookmakers'][0]
        mkt = bm['markets'][0]
        out = mkt['outcomes'][0]
        
        # تست با ضریب درست (باید تایید شود)
        opp_valid = {
            "event_id": event['id'],
            "sport_key": event['sport_key'],
            "legs": [{
                "bookmaker": bm['key'],
                "market": mkt['key'],
                "outcome": out['name'],
                "odd": float(out['price'])
            }]
        }
        verified, reason = await verifier.verify(opp_valid)
        print(f"✅ ضریب واقعی: {'تایید شد' if verified else 'رد شد'} — {reason}")
        
        # تست با ضریب خیلی متفاوت (باید رد شود)
        opp_fake = {
            "event_id": event['id'],
            "sport_key": event['sport_key'],
            "legs": [{
                "bookmaker": bm['key'],
                "market": mkt['key'],
                "outcome": out['name'],
                "odd": float(out['price']) * 1.5  # ۵۰٪ بالاتر — غیرممکن
            }]
        }
        verified, reason = await verifier.verify(opp_fake)
        assert verified == False, "❌ باید رد شود"
        print(f"✅ ضریب جعلی: رد شد — {reason}")

if __name__ == "__main__":
    asyncio.run(test())
