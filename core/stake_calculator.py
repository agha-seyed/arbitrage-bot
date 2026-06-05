from config import settings
import structlog

log = structlog.get_logger()

class StakeCalculator:
    def calculate(self, opportunity: dict) -> dict:
        """
        محاسبه مبالغ شرط بر اساس سرمایه کل.
        سپس مبالغ را گرد می‌کند تا رباتیک به نظر نرسد (برای جلوگیری از بن شدن).
        اگر بعد از گرد کردن، آربیتراژ سودده نماند، سیگنال مسدود می‌شود.
        """
        odds = [leg['odd'] for leg in opportunity['legs']]
        ip_total = sum(1.0 / o for o in odds)
        if ip_total >= 1:
            return opportunity # Not an arbitrage
            
        investment = settings.TOTAL_BANKROLL_EUR * settings.MAX_SINGLE_BET_PCT
        target_payout = investment / ip_total
        
        # ۱. محاسبه مبالغ دقیق
        exact_stakes = []
        for leg in opportunity['legs']:
            exact_stakes.append(target_payout / leg['odd'])
            
        # ۲. گرد کردن هوشمند مبالغ
        rounded_stakes = [self._smart_round(s) for s in exact_stakes]
        total_rounded_stake = sum(rounded_stakes)
        
        # چک کردن مینیمم مبلغ
        if any(s < settings.MIN_STAKE_EUR for s in rounded_stakes):
            log.debug("stake_too_low", stakes=rounded_stakes)
            return opportunity
            
        # ۳. محاسبه مجدد سود با مبالغ گرد شده
        payouts = [stake * odd for stake, odd in zip(rounded_stakes, odds)]
        min_payout = min(payouts)
        actual_profit_eur = min_payout - total_rounded_stake
        
        # اگر با گرد کردن، آربیتراژ تبدیل به ضرر شد، آن را باطل کن
        if actual_profit_eur <= 0:
            log.info("rounding_destroyed_profit", exact=exact_stakes, rounded=rounded_stakes)
            return opportunity
            
        # ۴. ثبت نتایج
        actual_profit_pct = (actual_profit_eur / total_rounded_stake) * 100
        
        for idx, leg in enumerate(opportunity['legs']):
            leg['stake'] = rounded_stakes[idx]
            
        opportunity['profit_pct'] = round(actual_profit_pct, 2)
        opportunity['total_stake'] = round(total_rounded_stake, 2)
        opportunity['guaranteed_profit_eur'] = round(actual_profit_eur, 2)
        opportunity['stakes_calculated'] = True
        
        return opportunity
        
    def _smart_round(self, amount: float) -> float:
        """
        گرد کردن مبالغ به نزدیک‌ترین عدد صحیح یا مضرب ۵
        تا بوکمیکر متوجه نشود که یک ربات ریاضی در حال شرط‌بندی است.
        """
        if amount < 20:
            # زیر 20 یورو به نزدیک‌ترین عدد صحیح
            return float(round(amount))
        elif amount < 50:
            # بین 20 تا 50 یورو به نزدیک‌ترین مضرب 2.5 یا 5 (ساده‌سازی: به مضرب 5)
            return float(round(amount / 5.0) * 5)
        else:
            # بالای 50 یورو به نزدیک‌ترین مضرب 10
            return float(round(amount / 10.0) * 10)
