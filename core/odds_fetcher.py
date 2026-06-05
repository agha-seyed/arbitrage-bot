import asyncio
import aiohttp
import structlog
from typing import Optional
from config import settings

log = structlog.get_logger()

class OddsFetcher:
    """
    کلاس اصلی دریافت ضرایب.
    اگر منبع اول (The-Odds-API) جواب ندهد، از منبع دوم (OddsAPI.io) می‌خواند.
    """
    
    PRIMARY_BASE_URL = "https://api.the-odds-api.com/v4"
    FALLBACK_BASE_URL = "https://api.oddsapi.io/v4"   # منبع دوم
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.primary_key = settings.ODDS_API_KEY
        self.fallback_key = settings.ODDS_API_FALLBACK_KEY
        self._consecutive_failures = 0
        self._use_fallback = False
        
        # Parse bookmakers from string
        self.bookmakers = settings.BOOKMAKERS_LIST.replace(" ", "")
    
    async def get_odds(self, sport_key: str, markets: str = "h2h") -> Optional[list]:
        """
        ابتدا از منبع اصلی، اگر خطا داشت از منبع دوم می‌خواند.
        اگر ۳ بار پشت سر هم منبع اصلی خطا داد، به fallback سوئیچ می‌کند.
        """
        if not self._use_fallback:
            result = await self._fetch_primary(sport_key, markets)
            if result is not None:
                self._consecutive_failures = 0
                return result
            
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                self._use_fallback = True
                log.warning("switching_to_fallback_api", failures=self._consecutive_failures)
        
        # تلاش با منبع دوم
        result = await self._fetch_fallback(sport_key, markets)
        if result is not None:
            return result
        
        log.error("both_apis_failed", sport=sport_key)
        return None

    async def get_event_odds(self, sport_key: str, event_id: str) -> Optional[dict]:
        """
        گرفتن ضرایب فقط برای یک رویداد خاص جهت Double Check (Odds Verifier)
        """
        url = f"{self.PRIMARY_BASE_URL}/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": self.primary_key,
            "regions": "eu",
            "markets": "h2h,totals",
            "bookmakers": self.bookmakers,
            "oddsFormat": "decimal"
        }
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
                elif r.status == 429:
                    log.warning("primary_event_rate_limited")
                    return None
        except Exception as e:
            log.error("event_odds_exception", error=str(e))
        return None
    
    async def _fetch_primary(self, sport_key: str, markets: str) -> Optional[list]:
        url = f"{self.PRIMARY_BASE_URL}/sports/{sport_key}/odds"
        params = {
            "apiKey": self.primary_key,
            "regions": "eu",
            "markets": markets,
            "bookmakers": self.bookmakers,
            "oddsFormat": "decimal"
        }
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json()
                    for event in data:
                        event['sport_key'] = sport_key
                    return data
                elif r.status == 429:
                    log.warning("primary_api_rate_limited")
                    return None
                else:
                    log.warning("primary_api_error", status=r.status)
                    return None
        except asyncio.TimeoutError:
            log.warning("primary_api_timeout")
            return None
        except Exception as e:
            log.error("primary_api_exception", error=str(e))
            return None
    
    async def _fetch_fallback(self, sport_key: str, markets: str) -> Optional[list]:
        """
        منبع دوم ساختار متفاوتی ممکن است داشته باشد.
        باید response را به فرمت یکسان تبدیل کند.
        """
        if not self.fallback_key:
            return None
            
        url = f"{self.FALLBACK_BASE_URL}/sports/{sport_key}/odds"
        params = {"api_key": self.fallback_key, "regions": "eu", "markets": markets}
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    raw = await r.json()
                    return self._normalize_fallback_response(raw)
                return None
        except Exception as e:
            log.error("fallback_api_exception", error=str(e))
            return None
    
    def _normalize_fallback_response(self, raw: list) -> list:
        """
        پاسخ منبع دوم را به فرمت یکسان The-Odds-API تبدیل کن.
        """
        normalized = []
        for event in raw:
            normalized.append({
                "id": event.get("id") or event.get("event_id"),
                "sport_key": event.get("sport_key") or event.get("sport"),
                "commence_time": event.get("commence_time") or event.get("start_time"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "bookmakers": event.get("bookmakers", [])
            })
        return normalized
