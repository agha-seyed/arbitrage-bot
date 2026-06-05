# core/surebet_client.py — GOD MODE v8.1
import asyncio
import aiohttp
from loguru import logger
import os

class SurebetClient:
        self.api_key = os.getenv("THE_ODDS_API_KEY", "f9a8245e9324a014d9469483b41f35e0")
        self.session = None
        self.base_url = "https://api.the-odds-api.com/v4/sports/{}/odds"
        self.event_base_url = "https://api.the-odds-api.com/v4/sports/{}/events/{}/odds"
        self.default_params = {
            "apiKey": self.api_key,
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131 Safari/537.36"
        }

    async def fetch_odds(self, sport, regions, markets):
        """دریافت odds و پیدا کردن آربیتراژ"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
        endpoint = self.base_url.format(sport)
        params = self.default_params.copy()
        params["regions"] = regions
        params["markets"] = markets

        for attempt in range(5):
            try:
                async with self.session.get(endpoint, params=params, headers=self.headers, timeout=25) as resp:
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

    async def fetch_event_odds(self, sport, event_id, regions, markets):
        """گرفتن ضرایب تازه فقط برای یک مسابقه خاص (جهت Double Check)"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            
        endpoint = self.event_base_url.format(sport, event_id)
        params = self.default_params.copy()
        params["regions"] = regions
        params["markets"] = markets

        try:
            async with self.session.get(endpoint, params=params, headers=self.headers, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    logger.warning("Rate limit on double check.")
                    return None
        except Exception as e:
            logger.error(f"خطا در دریافت ضرایب تکی: {e}")
            return None
        return None

    def find_arbitrage(self, games):
        """پیدا کردن آربیتراژ از odds در هر دو مارکت H2H و Totals"""
        surebets = []
        ALLOWED_BOOKIES = {"snai", "sisal", "eurobet", "goldbet", "better", "planetwin365", "betflag", "bet365", "bet365_it", "pinnacle", "betfair", "betfair_it"}
        
        for game in games:
            event_id = game.get("id", "")
            commence_time = game.get("commence_time", "")
            home_team = game["home_team"]
            away_team = game["away_team"]
            bookmakers = game["bookmakers"]
            
            best_h2h = {"home": {"price": 0, "bookie": ""}, "away": {"price": 0, "bookie": ""}, "draw": {"price": 0, "bookie": ""}}
            best_totals = {}  # {point: {"Over": {...}, "Under": {...}}}
            
            for book in bookmakers:
                bookie_name_clean = book["title"].lower().replace(" ", "")
                if bookie_name_clean not in ALLOWED_BOOKIES:
                    continue
                
                for market in book["markets"]:
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home_team and outcome["price"] > best_h2h["home"]["price"]:
                                best_h2h["home"] = {"price": outcome["price"], "bookie": book["title"]}
                            elif outcome["name"] == away_team and outcome["price"] > best_h2h["away"]["price"]:
                                best_h2h["away"] = {"price": outcome["price"], "bookie": book["title"]}
                            elif outcome["name"] == "Draw" and outcome["price"] > best_h2h["draw"]["price"]:
                                best_h2h["draw"] = {"price": outcome["price"], "bookie": book["title"]}
                                
                    elif market["key"] == "totals":
                        for outcome in market["outcomes"]:
                            point = outcome.get("point")
                            if not point: continue
                            if point not in best_totals:
                                best_totals[point] = {"Over": {"price": 0, "bookie": ""}, "Under": {"price": 0, "bookie": ""}}
                            
                            name = outcome["name"]
                            if name in ["Over", "Under"] and outcome["price"] > best_totals[point][name]["price"]:
                                best_totals[point][name] = {"price": outcome["price"], "bookie": book["title"]}
            
            # بررسی مارکت H2H
            h_price, a_price, d_price = best_h2h["home"]["price"], best_h2h["away"]["price"], best_h2h["draw"]["price"]
            if h_price > 1 and a_price > 1:
                ip = 1/h_price + 1/a_price
                if d_price > 1:
                    ip += 1/d_price
                
                if ip < 1:
                    profit = (1 - ip) * 100
                    surebets.append({
                        "event_id": event_id,
                        "commence_time": commence_time,
                        "event": {"name": f"{home_team} vs {away_team}"},
                        "market": "H2H",
                        "profit": profit,
                        "prongs": [
                            {"bookmaker": best_h2h["home"]["bookie"], "odd": h_price, "betType": "1"},
                            {"bookmaker": best_h2h["draw"]["bookie"], "odd": d_price, "betType": "X"} if d_price > 1 else None,
                            {"bookmaker": best_h2h["away"]["bookie"], "odd": a_price, "betType": "2"}
                        ],
                        "id": hash(f"h2h_{home_team} vs {away_team}")
                    })
            
            # بررسی مارکت Totals (Over/Under)
            for point, data in best_totals.items():
                o_price, u_price = data["Over"]["price"], data["Under"]["price"]
                if o_price > 1 and u_price > 1:
                    ip = 1/o_price + 1/u_price
                    if ip < 1:
                        profit = (1 - ip) * 100
                        surebets.append({
                            "event_id": event_id,
                            "commence_time": commence_time,
                            "event": {"name": f"{home_team} vs {away_team} (O/U {point})"},
                            "market": "Totals",
                            "profit": profit,
                            "prongs": [
                                {"bookmaker": data["Over"]["bookie"], "odd": o_price, "betType": f"Over {point}"},
                                {"bookmaker": data["Under"]["bookie"], "odd": u_price, "betType": f"Under {point}"}
                            ],
                            "id": hash(f"ou_{point}_{home_team} vs {away_team}")
                        })
                        
        return [s for s in surebets if s["prongs"].count(None) == 0]