from filters.profit_filter import DynamicProfitFilter
from datetime import datetime, timedelta, timezone

def test():
    pf = DynamicProfitFilter()
    now = datetime.now(timezone.utc)
    
    # بازی ۳۰ دقیقه دیگر با سود ۲٪ — باید رد شود (آستانه ۳٪)
    opp_close = {
        "profit_pct": 2.0,
        "commence_time": (now + timedelta(minutes=30)).isoformat()
    }
    passed, reason = pf.should_pass(opp_close)
    assert passed == False, "❌ باید رد شود"
    print(f"✅ بازی نزدیک با سود کم: رد شد — {reason}")
    
    # بازی ۴۸ ساعت دیگر با سود ۱.۵٪ — باید قبول شود
    opp_far = {
        "profit_pct": 1.5,
        "commence_time": (now + timedelta(hours=48)).isoformat()
    }
    passed, reason = pf.should_pass(opp_far)
    assert passed == True, "❌ باید قبول شود"
    print(f"✅ بازی دور با سود کافی: قبول شد — {reason}")
    
    print("✅ DynamicProfitFilter درست کار میکند")

if __name__ == "__main__":
    test()
