import pytest
from filters.bookmaker_classifier import BookmakerClassifier
from filters.profit_filter import DynamicProfitFilter
from datetime import datetime, timezone, timedelta

def test_bookmaker_classifier():
    classifier = BookmakerClassifier()
    
    assert classifier.classify('pinnacle') == 'sharp'
    assert classifier.classify('snai') == 'soft'
    assert classifier.classify('unknown_bookie') == 'unknown'
    
    # تست ارزیابی کیفیت
    opp_high = {"legs": [{"bookmaker": "snai"}, {"bookmaker": "eurobet"}]}
    assert classifier.evaluate(opp_high)['quality'] == 'HIGH'
    
    opp_medium = {"legs": [{"bookmaker": "snai"}, {"bookmaker": "pinnacle"}]}
    assert classifier.evaluate(opp_medium)['quality'] == 'MEDIUM'
    
    opp_low = {"legs": [{"bookmaker": "pinnacle"}, {"bookmaker": "betfair_ex"}]}
    assert classifier.evaluate(opp_low)['quality'] == 'LOW'

def test_profit_filter():
    profit_filter = DynamicProfitFilter()
    
    # بازی ۳ ساعت دیگر است (نیاز به 2 درصد سود دارد)
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    
    opp_pass = {"profit_pct": 2.5, "commence_time": future_time}
    passed, _ = profit_filter.should_pass(opp_pass)
    assert passed is True
    
    opp_fail = {"profit_pct": 1.5, "commence_time": future_time}
    passed, _ = profit_filter.should_pass(opp_fail)
    assert passed is False
    
    # بازی ۳۰ دقیقه دیگر است (نیاز به 3 درصد سود دارد)
    very_close_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    opp_very_close = {"profit_pct": 2.5, "commence_time": very_close_time}
    passed, _ = profit_filter.should_pass(opp_very_close)
    assert passed is False
