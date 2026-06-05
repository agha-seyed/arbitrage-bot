import asyncio
import time
from typing import Optional
from core.odds_fetcher import OddsFetcher
from config import settings
import structlog

log = structlog.get_logger()

class OddsVerifier:
    """
    قبل از ارسال هر آربیتراژ به تلگرام، این کلاس اجرا می‌شود.
    اگر در فاصله پیدا شدن آربیتراژ تا ارسال، ضریب بیش از MAX_DEVIATION تغییر
    کرده باشد یا مارکت بسته شده باشد، سیگنال را REJECT می‌کند.
    """
    
    def __init__(self, fetcher: OddsFetcher):
        self.fetcher = fetcher
        self.max_deviation = settings.MAX_ODDS_DEVIATION  # پیش‌فرض: 0.02 (2%)
        self.verify_delay = settings.VERIFY_DELAY_SECONDS  # پیش‌فرض: 1.0
    
    async def verify(self, opportunity: dict) -> tuple[bool, str]:
        """
        ورودی: یک دیکشنری آربیتراژ با کلیدهای:
          - event_id: str
          - sport_key: str
          - legs: list[dict] هر leg دارای bookmaker, market, outcome, odd
        
        خروجی: (True, "OK") یا (False, دلیل رد شدن)
        """
        await asyncio.sleep(self.verify_delay)
        
        try:
            fresh_data = await self.fetcher.get_event_odds(
                sport_key=opportunity['sport_key'],
                event_id=opportunity['event_id']
            )
        except Exception as e:
            log.warning("odds_verify_failed", error=str(e), event_id=opportunity['event_id'])
            return False, f"API_ERROR: {e}"
        
        if fresh_data is None:
            log.info("market_closed", event_id=opportunity['event_id'])
            return False, "MARKET_CLOSED"
        
        for leg in opportunity['legs']:
            current_odd = self._extract_odd(
                fresh_data,
                leg['bookmaker'],
                leg['market'],
                leg['outcome']
            )
            
            if current_odd is None:
                log.info("leg_unavailable", bookmaker=leg['bookmaker'], market=leg['market'])
                return False, f"LEG_UNAVAILABLE:{leg['bookmaker']}"
            
            original_odd = leg['odd']
            deviation = abs(current_odd - original_odd) / original_odd
            
            if deviation > self.max_deviation:
                log.info(
                    "odds_changed_too_much",
                    bookmaker=leg['bookmaker'],
                    original=original_odd,
                    current=current_odd,
                    deviation_pct=round(deviation * 100, 2)
                )
                return False, f"ODDS_CHANGED:{deviation*100:.1f}%"
            
            # ضریب جدید را در leg به‌روز کن (برای محاسبه دقیق‌تر سود)
            leg['verified_odd'] = current_odd
        
        log.info("odds_verified_ok", event_id=opportunity['event_id'])
        return True, "OK"
    
    def _extract_odd(self, data: dict, bookmaker: str, market: str, outcome: str) -> Optional[float]:
        """ضریب یک پیامد مشخص را از داده API استخراج کن"""
        for bm in data.get('bookmakers', []):
            if bm['key'] != bookmaker:
                continue
            for mkt in bm.get('markets', []):
                if mkt['key'] != market:
                    continue
                for out in mkt.get('outcomes', []):
                    if out['name'] == outcome:
                        return float(out['price'])
        return None
