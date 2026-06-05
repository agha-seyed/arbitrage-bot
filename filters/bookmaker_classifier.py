class BookmakerClassifier:
    
    SHARP = frozenset(["pinnacle", "betfair_ex", "matchbook", "betdaq"])
    
    SOFT = frozenset([
        "snai", "eurobet", "sisal", "bet365_it", "lottomatica",
        "goldbet", "planetwin365", "better", "admiralbet",
        "unibet_it", "william_hill", "bwin"
    ])
    
    def classify(self, bookmaker_key: str) -> str:
        """'sharp', 'soft', یا 'unknown' برمی‌گرداند"""
        if bookmaker_key in self.SHARP:
            return 'sharp'
        if bookmaker_key in self.SOFT:
            return 'soft'
        return 'unknown'
    
    def evaluate(self, opportunity: dict) -> dict:
        """
        کیفیت کلی یک آربیتراژ را ارزیابی می‌کند.
        
        نتیجه:
        - HIGH: همه طرف‌ها soft → ایمن و قابل اعتماد
        - MEDIUM: حداقل یک طرف sharp → ممکن است palpable error باشد
        - LOW: هر دو طرف sharp → احتمالاً خطای دیتابیس
        """
        types = [self.classify(leg['bookmaker']) for leg in opportunity['legs']]
        
        sharp_count = types.count('sharp')
        soft_count = types.count('soft')
        
        if sharp_count == 0:
            return {
                "quality": "HIGH",
                "risk": "LOW",
                "emoji": "🟢",
                "recommended": True,
                "note": "هر دو طرف سایت‌های soft هستند"
            }
        elif sharp_count == len(types):
            return {
                "quality": "LOW",
                "risk": "DATA_ERROR",
                "emoji": "🔴",
                "recommended": False,    # ← این سیگنال ارسال نمی‌شود
                "note": "هر دو طرف sharp — احتمالاً خطای داده"
            }
        else:
            return {
                "quality": "MEDIUM",
                "risk": "PALPABLE_ERROR_POSSIBLE",
                "emoji": "🟡",
                "recommended": True,
                "note": "یک طرف sharp — با احتیاط"
            }
