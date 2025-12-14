# core/surebet_client.py — نسخه جدید با The-Odds-API رایگان 🚀
# توضیح فارسی:
# این فایل odds واقعی از بوکی‌ها می‌گیره (با API Key رایگان تو)
# آربیتراژ رو خودش حساب می‌کنه (سود واقعی — بدون محدودیت ۱٪)
# هر درخواست یک سیگنال ممکنه بده — ۵۰۰ درخواست رایگان در ماه
# هیچ توکن تست یا اشتراکی لازم نیست!

import asyncio
import aiohttp
from loguru import logger
from datetime import datetime

class SurebetClient:
    def __init__(self):
        # API Key رایگان تو از The-Odds-API
        self.api_key = "f9a8245e9324a014d9469483b41f35e0"  # اینو با کلید خودت جایگزین کن اگر خواستی
        
        # endpoint برای odds فوتبال اروپا
        self.endpoint = "https://api.the-odds-api.com/v4/sports/soccer_italy_serie_a/odds"
        
        self.params = {
            "apiKey": self.api_key,
            "regions": "eu",  # اروپا
            "markets": "h2h",  # head to head (1X2)
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131 Safari/537.36"
        }

    async def fetch(self):
        """دریافت odds و پیدا کردن آربیتراژ"""
        async with aiohttp.ClientSession() as session:
            for attempt in range(5):
                try:
                    async with session.get(self.endpoint, params=self.params, headers=self.headers, timeout=25) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            logger.info(f"داده از The-Odds-API گرفته شد — {len(data)} بازی")
                            surebets = self.find_arbitrage(data)
                            if surebets:
                                logger.info(f"{len(surebets)} آربیتراژ پیدا شد")
                                return {"surebets": surebets}
                            return {"surebets": []}
                        elif resp.status == 429:
                            logger.warning("Rate limit — ۶۰ ثانیه صبر")
                            await asyncio.sleep(60)
                        else:
                            logger.warning(f"خطای API — وضعیت {resp.status}")
                            await asyncio.sleep(20)
                except Exception as e:
                    logger.error(f"خطای شبکه: {e}")
                    await asyncio.sleep(20)
            return {"surebets": []}

    def find_arbitrage(self, games):
        """پیدا کردن آربیتراژ از odds"""
        surebets = []
        for game in games:
            home_team = game["home_team"]
            away_team = game["away_team"]
            bookmakers = game["bookmakers"]
            
            best_home = 0
            best_away = 0
            best_draw = 0
            best_home_book = ""
            best_away_book = ""
            best_draw_book = ""
            
            for book in bookmakers:
                for market in book["markets"]:
                    if market["key"] == "h2h":
                        outcomes = market["outcomes"]
                        for outcome in outcomes:
                            if outcome["name"] == home_team:
                                if outcome["price"] > best_home:
                                    best_home = outcome["price"]
                                    best_home_book = book["title"]
                            elif outcome["name"] == away_team:
                                if outcome["price"] > best_away:
                                    best_away = outcome["price"]
                                    best_away_book = book["title"]
                            elif outcome["name"] == "Draw":
                                if outcome["price"] > best_draw:
                                    best_draw = outcome["price"]
                                    best_draw_book = book["title"]
            
            # حساب کردن آربیتراژ
            if best_home > 1 and best_away > 1:
                ip = 1/best_home + 1/best_away
                if best_draw > 1:
                    ip += 1/best_draw
                
                if ip < 1:
                    profit = (1 - ip) * 100
                    surebets.append({
                        "event": {"name": f"{home_team} vs {away_team}"},
                        "profit": profit,
                        "prongs": [
                            {"bookmaker": best_home_book, "odd": best_home, "betType": "1"},
                            {"bookmaker": best_away_book, "odd": best_away, "betType": "2"},
                            {"bookmaker": best_draw_book, "odd": best_draw, "betType": "X"} if best_draw > 1 else None
                        ],
                        "id": hash(f"{home_team} vs {away_team}")
                    })
        return [s for s in surebets if s["prongs"].count(None) == 0]  # فقط 3 لگ کامل