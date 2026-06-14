import asyncio
import aiohttp
import structlog
from typing import Optional
from config import settings

log = structlog.get_logger()

class OddsFetcher:
    """
    کلاس اصلی دریافت ضرایب.
    با قابلیت پشتیبانی از بی‌نهایت کلید API و چرخش خودکار کلیدها (API Key Rotation)
    برای جلوگیری از قطعی در صورت اتمام شارژ (401) یا محدودیت ریت (429).
    """
    
    PRIMARY_BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        
        # Load API keys and clean them up
        raw_keys = settings.ODDS_API_KEYS.split(',')
        self.api_keys = [k.strip() for k in raw_keys if k.strip()]
        
        if not self.api_keys:
            log.warning("no_api_keys_configured")
            
        self.current_key_idx = 0
        
        # Parse bookmakers from string
        self.bookmakers = settings.BOOKMAKERS_LIST.replace(" ", "")
        
    def _get_current_key(self) -> str:
        if not self.api_keys:
            return ""
        return self.api_keys[self.current_key_idx]
        
    def _rotate_key(self):
        if not self.api_keys:
            return
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        log.warning("api_key_rotated", new_idx=self.current_key_idx)
    
    async def get_odds(self, sport_key: str, markets: str = "h2h") -> Optional[list]:
        """
        دریافت ضرایب. در صورت برخورد به ۴۰۱ یا ۴۲۹ کلید را می‌چرخاند و دوباره تلاش می‌کند.
        """
        if not self.api_keys:
            return None
            
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            url = f"{self.PRIMARY_BASE_URL}/sports/{sport_key}/odds"
            params = {
                "apiKey": self._get_current_key(),
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
                    elif r.status in [401, 429]:
                        log.warning("api_key_exhausted_or_limited", status=r.status, key_idx=self.current_key_idx)
                        self._rotate_key()
                        continue
                    else:
                        log.warning("primary_api_error", status=r.status)
                        return None
            except asyncio.TimeoutError:
                log.warning("primary_api_timeout")
                return None
            except Exception as e:
                log.error("primary_api_exception", error=str(e))
                return None
                
        log.error("all_api_keys_exhausted_or_failed", sport=sport_key)
        return None

    async def get_event_odds(self, sport_key: str, event_id: str) -> Optional[dict]:
        """
        گرفتن ضرایب فقط برای یک رویداد خاص جهت Double Check (Odds Verifier)
        با پشتیبانی از چرخش کلید.
        """
        if not self.api_keys:
            return None
            
        max_attempts = len(self.api_keys)
        
        for attempt in range(max_attempts):
            url = f"{self.PRIMARY_BASE_URL}/sports/{sport_key}/events/{event_id}/odds"
            params = {
                "apiKey": self._get_current_key(),
                "regions": "eu",
                "markets": "h2h,totals",
                "bookmakers": self.bookmakers,
                "oddsFormat": "decimal"
            }
            try:
                async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        return await r.json()
                    elif r.status in [401, 429]:
                        log.warning("event_api_key_exhausted_or_limited", status=r.status, key_idx=self.current_key_idx)
                        self._rotate_key()
                        continue
                    else:
                        return None
            except Exception as e:
                log.error("event_odds_exception", error=str(e))
                return None
                
        return None
