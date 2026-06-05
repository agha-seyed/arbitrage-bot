# engine/arbitrage_engine.py — GOD MODE v8.1 🚀
# توضیح فارسی: این فایل مغز ربات است. سیگنال‌ها رو تحلیل می‌کنه، stake محاسبه می‌کنه،
# چک می‌کنه که رویداد خطرناک نباشه، و فقط سیگنال‌های امن رو می‌فرسته.

import random
import redis.asyncio as redis
import os
import json
from datetime import datetime, timezone
from loguru import logger

from engine.health_monitor import AccountHealthMonitor
from engine.steam_detector import SteamDetector

def calculate_min_profit_threshold(hours_to_event: float) -> float:
    """
    آستانه سود حداقل بر اساس زمان تا شروع بازی:
    - بیش از 24 ساعت: حداقل 1.0% سود
    - 6 تا 24 ساعت: حداقل 1.5% سود  
    - 1 تا 6 ساعت: حداقل 2.0% سود
    - کمتر از 1 ساعت: حداقل 3.0% سود
    """
    if hours_to_event > 24:
        return 1.0
    elif hours_to_event > 6:
        return 1.5
    elif hours_to_event > 1:
        return 2.0
    else:
        return 3.0

BOOKMAKER_CLASSIFICATION = {
    "sharp": ["pinnacle", "betfair_ex", "betfair_it", "betfair", "matchbook"],
    "soft": ["snai", "eurobet", "sisal", "bet365", "bet365_it", "lottomatica", 
             "goldbet", "planetwin365", "better", "admiralbet", "betflag"]
}

def classify_bookmaker(bookmaker: str) -> str:
    b = bookmaker.lower().replace(" ", "")
    for category, list_of_bookies in BOOKMAKER_CLASSIFICATION.items():
        if b in list_of_bookies:
            return category
    return "soft"

def evaluate_arbitrage_quality(bookies: list) -> dict:
    legs_classification = [classify_bookmaker(b) for b in bookies]
    
    if all(c == 'soft' for c in legs_classification):
        return {"quality": "HIGH", "risk": "LOW", "recommended": True}
    elif any(c == 'sharp' for c in legs_classification) and any(c == 'soft' for c in legs_classification):
        return {"quality": "MEDIUM", "risk": "PALPABLE_ERROR_POSSIBLE", "recommended": True}
    else:
        return {"quality": "LOW", "risk": "DATA_ERROR", "recommended": False}

def calculate_urgency_score(hours_to_event: float, profit_pct: float) -> dict:
    if hours_to_event < 0.5 and profit_pct > 3.0:
        return {"urgency": "🚨 CLOSING FAST", "action": "ممکن است بسته شود"}
    elif hours_to_event < 2 and profit_pct > 2.0:
        return {"urgency": "⚡ URGENT", "action": "سریع عمل کنید"}
    elif hours_to_event > 24 and profit_pct > 1.5:
        return {"urgency": "💎 PREMIUM", "action": "فرصت عالی"}
    else:
        return {"urgency": "📊 NORMAL", "action": "معمولی"}

# DRY_RUN برای تست بدون ثبت واقعی
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

r = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

health_monitor = AccountHealthMonitor(r)
steam_detector = SteamDetector(r)

# تنظیمات برای تست اولیه (سرمایه کم)
MAX_DAILY_EXPOSURE_PER_BOOKIE = 3000  # برای تست ایمن
DAILY_TOTAL_EXPOSURE_LIMIT = 8000
KELLY_FRACTION = 0.2  # محافظه‌کارانه برای تست

# حداقل و حداکثر stake برای تست
MIN_STAKE = 25
MAX_STAKE = 300

BOOKIE_MAX_STAKE = {
    "snai": 1000, "sisal": 800, "eurobet": 600, "goldbet": 600,
    "better": 500, "planetwin365": 600, "betflag": 2000, "bet365_it": 1500,
    "pinnacle": 5000, "betfair_it": 6000
}

# اعداد رند طبیعی
ROUNDING = [25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,110,125,150,175,200,225,250,275,300]

def human_round(amount: float) -> int:
    """رند کردن طبیعی — برای تست ایمن"""
    if amount < MIN_STAKE:
        return MIN_STAKE
    closest = min(ROUNDING, key=lambda x: abs(x - amount))
    variance = random.choice([-5,0,5,10,-10])
    final = closest + variance
    final = max(MIN_STAKE, min(final, MAX_STAKE))
    return int(final)

async def check_daily_exposure(bookie: str, stake: int) -> bool:
    if DRY_RUN:
        logger.info(f"[تست] چک exposure برای {bookie} — stake {stake} € — مجاز")
        return True
    
    key = f"exp:{datetime.now(timezone.utc):%Y-%m-%d}:{bookie.lower()}"
    current = int(await r.get(key) or 0)
    if current + stake > MAX_DAILY_EXPOSURE_PER_BOOKIE:
        logger.warning(f"حد روزانه {bookie} پر شد")
        return False
    await r.incrby(key, stake)
    await r.expire(key, 86400)
    return True

def calculate_stakes(total_bankroll: float, odds: list, profit_pct: float, bookies: list) -> list | None:
    ip_total = sum(1.0 / o for o in odds)
    if ip_total >= 1:
        return None
        
    # فاز 4: مدیریت سرمایه خرد (Micro-Bankroll) - جلوگیری از ورشکستگی
    # حداکثر 20% از کل بانک‌رول را در یک شرط درگیر می‌کنیم
    max_allocation_pct = 0.20
    investment = total_bankroll * max_allocation_pct
    
    target_payout = investment / ip_total
    stakes = []
    
    for o, b in zip(odds, bookies):
        s = round(target_payout / o, 2)
        
        # کنترل حداقل شرط سایت‌ها (Minimum Bet معمولاً 2 یورو است)
        if s < 2.0:
            logger.info(f"مبلغ سهم سایت {b} کمتر از 2 یورو ({s}) شد — آربیتراژ لغو گردید.")
            return None
            
        stakes.append(s)
        
    return stakes

async def is_seen(event_id: str) -> bool:
    key = f"seen:{event_id}"
    if await r.get(key):
        return True
    await r.setex(key, 95, "1")
    return False

async def build_signal(arb: dict, bankroll: float, source: str) -> dict | None:
    try:
        profit_pct = float(arb.get("profit", 0))
        
        event = arb["event"]["name"]
        event_id = arb.get("event_id", str(arb.get("id", "")))
        commence_time_str = arb.get("commence_time", "")
        
        hours_to_event = 48.0 # default if not found
        if commence_time_str:
            try:
                # Format: "2023-10-10T14:30:00Z"
                commence_time = datetime.strptime(commence_time_str, "%Y-%m-%dT%H:%M:%SZ")
                time_diff = commence_time - datetime.utcnow()
                hours_to_event = time_diff.total_seconds() / 3600.0
            except Exception as e:
                logger.warning(f"Error parsing commence_time {commence_time_str}: {e}")
                
        min_threshold = calculate_min_profit_threshold(hours_to_event)
        
        if profit_pct < min_threshold:
            logger.info(f"سیگنال رد شد: {event} سود {profit_pct:.2f}% کمتر از حدنصاب {min_threshold}% (ساعت تا شروع: {hours_to_event:.1f})")
            return None
            
        if await is_seen(event_id):
            return None
        
        prongs = arb["prongs"]
        if len(prongs) < 2:
            return None
        
        odds = [float(p["odd"]) for p in prongs]
        bookies = [p["bookmaker"] for p in prongs]
        
        quality_data = evaluate_arbitrage_quality(bookies)
        if not quality_data["recommended"]:
            logger.info(f"سیگنال بی‌کیفیت (احتمال خطای دیتا) رد شد: {event}")
            return None
            
        urgency_data = calculate_urgency_score(hours_to_event, profit_pct)
        
        ip_total = sum(1.0 / o for o in odds)
        stakes = calculate_stakes(bankroll, odds, profit_pct, bookies)
        if not stakes:
            return None
        
        total_stake = sum(stakes)
        profit_eur = round(total_stake * (profit_pct / 100), 2)
        
        legs = []
        for p, s in zip(prongs, stakes):
            b = p["bookmaker"].lower().replace(" ", "")
            
            # 1. Health Check
            health_score = await health_monitor.calculate_health_score(b)
            if health_score < 50:
                logger.warning(f"بوکمیکر {b} نمره سلامت پایینی دارد ({health_score}) - سیگنال رد شد")
                return None
                
            # 2. Steam Detection
            bet_type = p.get("betType", "1X2")
            await steam_detector.record_odd_snapshot(event_id, b, bet_type, float(p["odd"]))
            if await steam_detector.detect_steam(event_id, b, bet_type):
                logger.warning(f"سیگنال {event} به دلیل Steam (نوسان ناگهانی ضریب) در {b} رد شد")
                return None
            
            if not await check_daily_exposure(b, s):
                return None
                
            # محاسبه احتمال واقعی (بدون حاشیه سود) و درصد ارزش شرط
            true_prob = (1.0 / float(p["odd"])) / ip_total
            true_odd = 1.0 / true_prob if true_prob > 0 else float(p["odd"])
            value_pct = round((float(p["odd"]) / true_odd - 1) * 100, 2)
            
            legs.append({
                "bookie": b,
                "selection": p.get("betType", "1X2"),
                "odd": p["odd"],
                "true_odd": round(true_odd, 2),
                "value_pct": value_pct,
                "stake": s,
                "link": p.get("link", f"https://www.{b}.it")
            })
        
        return {
            "event": event,
            "profit_pct": round(profit_pct, 2),
            "total_stake": total_stake,
            "guaranteed_profit": profit_eur,
            "legs": legs,
            "id": event_id,
            "source": source,
            "quality": quality_data["quality"],
            "urgency": urgency_data["urgency"],
            "action_advice": urgency_data["action"]
        }
    except Exception as e:
        logger.error(f"خطا در ساخت سیگنال: {e}")
        return None

async def save_signal_to_redis(signal: dict):
    try:
        # Save timestamp
        signal["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        await r.lpush("recent_signals", json.dumps(signal))
        await r.ltrim("recent_signals", 0, 49) # Keep last 50
    except Exception as e:
        logger.error(f"خطا در ذخیره سیگنال در ردیس: {e}")