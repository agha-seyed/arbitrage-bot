from datetime import datetime, timezone
from config import settings
import structlog

log = structlog.get_logger()

class DynamicProfitFilter:
    """
    آستانه حداقل سود را بر اساس زمان تا شروع بازی محاسبه می‌کند.
    هرچه بازی نزدیک‌تر باشد، آستانه بالاتر است (چون احتمال بسته شدن مارکت بیشتر است).
    """
    
    # این مقادیر از .env خوانده می‌شوند
    @property
    def THRESHOLDS(self):
        return {
            'very_close':  (0,    1,   settings.MIN_PROFIT_VERY_CLOSE),   # پیش‌فرض: 3.0%
            'close':       (1,    6,   settings.MIN_PROFIT_CLOSE),         # پیش‌فرض: 2.0%
            'medium':      (6,    24,  settings.MIN_PROFIT_MEDIUM),        # پیش‌فرض: 1.5%
            'far':         (24,   999, settings.MIN_PROFIT_FAR),           # پیش‌فرض: 1.0%
        }
    
    def should_pass(self, opportunity: dict) -> tuple[bool, str]:
        """
        ورودی: دیکشنری آربیتراژ با کلیدهای profit_pct و commence_time
        خروجی: (True, دلیل) یا (False, دلیل رد)
        """
        profit_pct = opportunity['profit_pct']
        commence_time_str = opportunity['commence_time']
        
        # Handle "Z" suffix for ISO format correctly across Python versions
        if commence_time_str.endswith("Z"):
            commence_time_str = commence_time_str[:-1] + "+00:00"
            
        commence_time = datetime.fromisoformat(commence_time_str)
        
        if commence_time.tzinfo is None:
            commence_time = commence_time.replace(tzinfo=timezone.utc)
        
        hours_to_event = (commence_time - datetime.now(timezone.utc)).total_seconds() / 3600
        hours_to_event = max(0, hours_to_event)
        
        threshold = self._get_threshold(hours_to_event)
        
        if profit_pct < threshold:
            log.debug(
                "profit_filtered",
                profit_pct=profit_pct,
                threshold=threshold,
                hours_to_event=round(hours_to_event, 1)
            )
            return False, f"PROFIT_TOO_LOW:{profit_pct:.2f}%<{threshold}%"
        
        return True, f"PROFIT_OK:{profit_pct:.2f}%"
    
    def get_urgency_label(self, hours_to_event: float, profit_pct: float) -> dict:
        """برچسب فوریت برای پیام تلگرام"""
        if hours_to_event < 0.5 and profit_pct > 3.0:
            return {"emoji": "🚨", "label": "CLOSING FAST", "note": "مارکت دارد می‌بندد"}
        elif hours_to_event < 2:
            return {"emoji": "⚡", "label": "URGENT",       "note": "سریع عمل کنید"}
        elif hours_to_event > 24 and profit_pct > 1.5:
            return {"emoji": "💎", "label": "PREMIUM",      "note": "فرصت عالی"}
        else:
            return {"emoji": "📊", "label": "NORMAL",       "note": ""}
    
    def _get_threshold(self, hours: float) -> float:
        for name, (min_h, max_h, thresh) in self.THRESHOLDS.items():
            if min_h <= hours < max_h:
                return thresh
        return self.THRESHOLDS['far'][2]
