class VigRemover:
    def calculate_true_odds(self, opportunity: dict) -> dict:
        """
        محاسبه احتمال واقعی (بدون حاشیه سود) برای هر رویداد.
        """
        if 'stakes_calculated' not in opportunity:
            return opportunity
            
        odds = [leg['odd'] for leg in opportunity['legs']]
        ip_total = sum(1.0 / o for o in odds)
        
        for leg in opportunity['legs']:
            true_prob = (1.0 / leg['odd']) / ip_total
            true_odd = 1.0 / true_prob if true_prob > 0 else leg['odd']
            value_pct = round((leg['odd'] / true_odd - 1) * 100, 2)
            
            leg['true_odd'] = round(true_odd, 2)
            leg['value_pct'] = value_pct
            
        return opportunity
