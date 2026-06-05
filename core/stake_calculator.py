from config import settings

class StakeCalculator:
    def calculate(self, opportunity: dict) -> dict:
        """
        محاسبه مبالغ شرط بر اساس سرمایه کل و درصد درگیری.
        اگر سهم سایتی کمتر از MIN_STAKE_EUR شود، سیگنال مسدود می‌شود (محاسبه ناموفق).
        """
        odds = [leg['odd'] for leg in opportunity['legs']]
        ip_total = sum(1.0 / o for o in odds)
        if ip_total >= 1:
            return opportunity # Not an arbitrage
            
        investment = settings.TOTAL_BANKROLL_EUR * settings.MAX_SINGLE_BET_PCT
        target_payout = investment / ip_total
        
        total_stake = 0
        
        for leg in opportunity['legs']:
            s = round(target_payout / leg['odd'], 2)
            if s < settings.MIN_STAKE_EUR:
                # اگر مبلغ یکی از شرط‌ها از مینیمم مجاز کمتر شد، محاسبه باطل است
                return opportunity # Failed to calculate valid stakes
            leg['stake'] = s
            total_stake += s
            
        opportunity['total_stake'] = round(total_stake, 2)
        opportunity['guaranteed_profit_eur'] = round(total_stake * (opportunity['profit_pct'] / 100), 2)
        opportunity['stakes_calculated'] = True
        return opportunity
