import structlog
from filters.odds_verifier import OddsVerifier
from filters.profit_filter import DynamicProfitFilter
from filters.bookmaker_classifier import BookmakerClassifier
from filters.steam_detector import SteamDetector
from protection.account_health import AccountHealthMonitor
from protection.exposure_control import ExposureController

log = structlog.get_logger()

class FilterPipeline:
    """
    تمام فیلترها را به ترتیب اجرا می‌کند.
    اگر هر فیلتری رد کند، بقیه فیلترها اجرا نمی‌شوند (fail fast).
    
    ترتیب اجرا (از سریع‌ترین به کندترین):
    1. Steam Detector (چک Redis — بسیار سریع)
    2. Bookmaker Quality (چک دیکشنری — فوری)
    3. Account Health (چک Redis — سریع)
    4. Exposure Control (چک Redis — سریع)
    5. Profit Filter (محاسبه ریاضی — فوری)
    6. Odds Verifier (API call — کند، اما مهم‌ترین)
    """
    
    def __init__(self, verifier: OddsVerifier, profit_filter: DynamicProfitFilter, 
                 classifier: BookmakerClassifier, steam_detector: SteamDetector, 
                 health_monitor: AccountHealthMonitor, exposure_controller: ExposureController):
        self.verifier = verifier
        self.profit_filter = profit_filter
        self.classifier = classifier
        self.steam_detector = steam_detector
        self.health_monitor = health_monitor
        self.exposure_controller = exposure_controller
    
    async def run(self, opportunity: dict) -> tuple[bool, dict]:
        """
        ورودی: یک opportunity خام از arb_calculator
        خروجی: (True, opportunity غنی‌شده) یا (False, {reason: ...})
        """
        event_id = opportunity.get('event_id', 'unknown')
        
        if not opportunity.get('legs'):
            return False, {"reason": "NO_LEGS"}
        
        # --- فیلتر ۱: کیفیت بوکمیکر --- (فوری تر است چون نیاز به await ندارد)
        quality = self.classifier.evaluate(opportunity)
        if quality['quality'] == 'LOW':
            log.info("pipeline_rejected", stage="classifier", event_id=event_id)
            return False, {"reason": "LOW_QUALITY_BOOKS"}
        opportunity['quality'] = quality
        
        # --- فیلتر ۲: Steam Detection ---
        for leg in opportunity['legs']:
            if await self.steam_detector.is_steaming(
                event_id, leg['bookmaker'], leg['market']
            ):
                log.info("pipeline_rejected", stage="steam", event_id=event_id)
                return False, {"reason": "STEAM_DETECTED", "leg": leg['bookmaker']}
        
        # --- فیلتر ۳: سلامت اکانت‌ها ---
        for leg in opportunity['legs']:
            score = await self.health_monitor.get_score(leg['bookmaker'])
            if score < 50:
                log.warning(
                    "pipeline_rejected", stage="health",
                    bookmaker=leg['bookmaker'], score=score
                )
                return False, {"reason": f"ACCOUNT_UNHEALTHY:{leg['bookmaker']}", "score": score}
        
        # --- فیلتر ۴: حداقل سود ---
        passed, msg = self.profit_filter.should_pass(opportunity)
        if not passed:
            log.debug("pipeline_rejected", stage="profit", reason=msg)
            return False, {"reason": msg}
        
        # اضافه کردن برچسب فوریت
        from datetime import datetime, timezone
        ct_str = opportunity['commence_time']
        if ct_str.endswith("Z"):
            ct_str = ct_str[:-1] + "+00:00"
        ct = datetime.fromisoformat(ct_str)
        if ct.tzinfo is None:
            ct = ct.replace(tzinfo=timezone.utc)
        hours = (ct - datetime.now(timezone.utc)).total_seconds() / 3600
        opportunity['urgency'] = self.profit_filter.get_urgency_label(
            hours, opportunity['profit_pct']
        )
        
        # --- فیلتر ۵: Exposure Control ---
        # این فیلتر باید بعد از Stake Calculator اجرا شود!
        # پس استثنائاً از خط لوله فیلترهای اولیه خارج می‌شود و در main.py بعد از محاسبه مبالغ کنترل می‌شود.
        # این مهم است چون بدون stake نمی‌توان exposure را بررسی کرد.
        
        # --- فیلتر ۶: تایید نهایی ضرایب (API call) ---
        verified, reason = await self.verifier.verify(opportunity)
        if not verified:
            log.info("pipeline_rejected", stage="verifier", reason=reason)
            return False, {"reason": reason}
        
        log.info("pipeline_approved", event_id=event_id, profit=opportunity['profit_pct'])
        return True, opportunity
