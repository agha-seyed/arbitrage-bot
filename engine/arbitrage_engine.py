# main.py — Italian Arbitrage Beast 2027 — GOD MODE v8.0 🚀💰
# توضیح فارسی: این فایل قلب ربات است. هر ۶۰ ثانیه داده از API تست Surebet می‌گیرد
# فقط سیگنال‌های با سود زیر ۱٪ می‌دهد (محدودیت تست)
# بعد از خرید توکن واقعی، سود بالای ۸٪ هم می‌گیری!

import asyncio
import os
import signal
import random
import sys
from datetime import datetime
from loguru import logger

from core.surebet_client import SurebetClient
from bot.telegram_bot import send_surebet_alert

# تنظیمات — از .env بگیر یا پیش‌فرض (برای تست)# engine/arbitrage_engine.py — GOD MODE v8.0 🚀
# توضیح فارسی: این فایل مغز ربات است. سیگنال‌ها رو تحلیل می‌کنه، stake محاسبه می‌کنه،
# چک می‌کنه که رویداد خطرناک نباشه، و فقط سیگنال‌های امن رو می‌فرسته.
# برای تست با API رایگان، سود زیر ۱٪ می‌ده، اما منطق کاملاً واقعی هست.

import random
import redis
import os
from datetime import datetime
from loguru import logger

# DRY_RUN برای تست بدون ثبت واقعی
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

r = redis.Redis(
    host='redis',  # همیشه redis — در Docker این نام container است
    port=6379,
    db=0,
    decode_responses=True
)

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

def check_daily_exposure(bookie: str, stake: int) -> bool:
    if DRY_RUN:
        logger.info(f"[تست] چک exposure برای {bookie} — stake {stake} € — مجاز")
        return True
    
    key = f"exp:{datetime.now():%Y-%m-%d}:{bookie.lower()}"
    current = int(r.get(key) or 0)
    if current + stake > MAX_DAILY_EXPOSURE_PER_BOOKIE:
        logger.warning(f"حد روزانه {bookie} پر شد")
        return False
    r.incrby(key, stake)
    r.expire(key, 86400)
    return True

def calculate_stakes(bankroll: float, odds: list, profit_pct: float, bookies: list) -> list:
    if not odds or any(o <= 1.01 for o in odds):
        return []
    
    ip_total = sum(1.0 / o for o in odds)
    base = bankroll * KELLY_FRACTION * (profit_pct / 100)
    
    stakes = []
    for i, odd in enumerate(odds):
        raw = (base / ip_total) / odd
        bookie = bookies[i].lower().replace(" ", "")
        max_allowed = BOOKIE_MAX_STAKE.get(bookie, 500)
        raw = min(raw, max_allowed * 0.9)
        stakes.append(human_round(raw))
    
    total = sum(stakes)
    if total > DAILY_TOTAL_EXPOSURE_LIMIT:
        scale = DAILY_TOTAL_EXPOSURE_LIMIT / total * 0.95
        stakes = [human_round(s * scale) for s in stakes]
    
    return stakes

def is_seen(event_id: str) -> bool:
    key = f"seen:{event_id}"
    if r.get(key):
        return True
    r.setex(key, 95, "1")
    return False

def build_signal(arb: dict, bankroll: float, source: str) -> dict | None:
    try:
        profit_pct = float(arb.get("profit", 0))
        if profit_pct < 0.1:  # در تست معمولاً زیر ۱٪ هست
            return None
        
        event = arb["event"]["name"]
        event_id = str(arb["id"])
        if is_seen(event_id):
            return None
        
        prongs = arb["prongs"]
        if len(prongs) < 2:
            return None
        
        odds = [float(p["odd"]) for p in prongs]
        bookies = [p["bookmaker"] for p in prongs]
        stakes = calculate_stakes(bankroll, odds, profit_pct, bookies)
        if not stakes:
            return None
        
        total_stake = sum(stakes)
        profit_eur = round(total_stake * (profit_pct / 100), 2)
        
        legs = []
        for p, s in zip(prongs, stakes):
            b = p["bookmaker"].lower().replace(" ", "")
            if not check_daily_exposure(b, s):
                return None
            legs.append({
                "bookie": b,
                "selection": p.get("betType", "1X2"),
                "odd": p["odd"],
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
            "source": source
        }
    except Exception as e:
        logger.error(f"خطا در ساخت سیگنال: {e}")
        return None
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"  # تست بدون ثبت واقعی
BANKROLL = float(os.getenv("BANKROLL", "5000"))  # سرمایه فرضی برای تست
FETCH_INTERVAL = 60  # دقیقاً ۶۰ ثانیه — محدودیت تست API
WATCHDOG_TIMEOUT = 300  # ۵ دقیقه بدون سیگنال = ری‌استارت

# Logging حرفه‌ای — لاگ‌ها در پوشه logs ذخیره می‌شن
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/arbitrage_{time:YYYY-MM-DD}.log", rotation="500 MB", retention="30 days", level="INFO")
logger.add("logs/errors_{time:YYYY-MM-DD}.log", level="ERROR", rotation="100 MB")

last_success = datetime.utcnow()

async def watchdog():
    """اگر ۵ دقیقه سیگنال نیاد، ربات رو ری‌استارت می‌کنه"""
    global last_success
    while True:
        await asyncio.sleep(60)
        if (datetime.utcnow() - last_success).total_seconds() > WATCHDOG_TIMEOUT:
            logger.critical("۵ دقیقه بدون سیگنال — ری‌استارت تمیز")
            os.kill(os.getpid(), signal.SIGTERM)

async def graceful_shutdown(signum, frame):
    """وقتی ربات متوقف شد، همه چیز رو تمیز می‌بنده"""
    logger.info(f"سیگنال {signal.Signals(signum).name} دریافت شد — خروج تمیز")
    await asyncio.sleep(0.5)
    sys.exit(0)

def setup_signal_handlers():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(graceful_shutdown(s, None)))

async def main():
    global last_success
    logger.info("Italian Arbitrage Beast 2027 — GOD MODE v8.0 فعال شد 🚀")
    logger.info("حالت تست API — سود زیر ۱٪ — هر ۶۰ ثانیه یک درخواست")
    if DRY_RUN:
        logger.warning("[DRY_RUN] فعال — هیچ stake واقعی ثبت نمی‌شه (تست امن)")
    
    if os.name != "nt":
        setup_signal_handlers()
    else:
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))
    
    asyncio.create_task(watchdog())
    
    client = SurebetClient()  # از توکن تست استفاده می‌کنه
    
    while True:
        try:
            data = await asyncio.wait_for(client.fetch(), timeout=30)
            if data and "surebets" in data:
                last_success = datetime.utcnow()
                count = len(data["surebets"])
                logger.info(f"{count} سیگنال تست پیدا شد — پردازش شروع شد")
                for arb in data["surebets"][:5]:  # فقط ۵ تا اول برای تست
                    event_name = arb["event"]["name"]
                    if is_blacklisted_event(event_name):
                        logger.info(f"رویداد بلاک‌لیست — رد شد: {event_name}")
                        continue
                    
                    signal = build_signal(arb, BANKROLL, "surebet_test")
                    if signal:
                        success = await send_surebet_alert(signal)
                        if success:
                            logger.success(f"سیگنال تست ارسال شد: {event_name} — {signal['profit_pct']}%")
                        await asyncio.sleep(random.uniform(5, 8))  # رفتار انسانی
            
            await asyncio.sleep(FETCH_INTERVAL)  # دقیقاً ۶۰ ثانیه صبر کن
            
        except Exception as e:
            logger.error(f"خطای غیرمهم (ادامه می‌دیم): {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())