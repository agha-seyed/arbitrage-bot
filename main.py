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
from engine.arbitrage_engine import build_signal, save_signal_to_redis, r, health_monitor
from engine.blacklist import is_blacklisted_event
from bot.telegram_bot import send_surebet_alert
from ml_predictor import ArbitragePredictor
from engine.clv_tracker import CLVTracker

clv_tracker = CLVTracker(r)

# List of sports to scan (GOD MODE Phase 3 Multi-Sport)
SPORTS = [
    "soccer_italy_serie_a", 
    "soccer_uefa_champs_league",
    "basketball_euroleague",
    "tennis_atp"
]
REGIONS = "eu"
MARKETS = "h2h,totals"  # تست بدون ثبت واقعی
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

async def verify_odds_before_alert(signal_data: dict, client: SurebetClient, sport: str) -> bool:
    """
    ضرایب را دقیقاً ۱ ثانیه قبل از ارسال، مجدداً از API دریافت می‌کند.
    اگر تفاوت بیش از ۲٪ باشد، آربیتراژ را رد می‌کند.
    """
    event_id = signal_data.get("id")
    if not event_id:
        return True
        
    await asyncio.sleep(1)
    
    fresh_data = await client.fetch_event_odds(sport, event_id, REGIONS, MARKETS)
    if not fresh_data:
        logger.warning(f"عدم دریافت داده تاییدیه برای {event_id} - رد کردن آربیتراژ برای امنیت")
        return False
        
    event_data = fresh_data[0] if isinstance(fresh_data, list) and len(fresh_data) > 0 else fresh_data
    if not event_data or "bookmakers" not in event_data:
        return False
        
    for leg in signal_data["legs"]:
        bookmaker = leg["bookie"]
        selection = leg["selection"]
        original_odd = float(leg["odd"])
        
        current_odd = None
        for b in event_data["bookmakers"]:
            if b["title"].lower().replace(" ", "") == bookmaker:
                for market in b["markets"]:
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if (selection == "1" and outcome["name"] == event_data.get("home_team")) or \
                               (selection == "2" and outcome["name"] == event_data.get("away_team")) or \
                               (selection == "X" and outcome["name"] == "Draw"):
                                current_odd = float(outcome["price"])
                    elif market["key"] == "totals":
                        for outcome in market["outcomes"]:
                            if selection.startswith(outcome["name"]) and str(outcome.get("point")) in selection:
                                current_odd = float(outcome["price"])
                break
        
        if not current_odd:
            logger.warning(f"ضریب {bookmaker} در تاییدیه یافت نشد (بسته شده) - رد کردن سیگنال")
            return False
            
        deviation = abs(current_odd - original_odd) / original_odd
        if deviation > 0.02:
            logger.warning(f"تغییر ضریب در {bookmaker}: قدیم {original_odd} جدید {current_odd} (تغییر {deviation*100:.1f}%) - رد شد")
            return False

    logger.info("تاییدیه با موفقیت انجام شد: ضریب‌ها معتبر هستند.")
    return True

async def main():
    global last_success
    logger.info("Italian Arbitrage Beast 2027 — GOD MODE v8.0 فعال شد 🚀")
    logger.info("ربات در حالت واقعی (Real Mode) قرار دارد. تمامی سیگنال‌ها پردازش می‌شوند.")
    
    if os.name != "nt":
        setup_signal_handlers()
    else:
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(graceful_shutdown(s, f)))
    
    asyncio.create_task(watchdog())
    
    client = SurebetClient()  # از توکن تست استفاده می‌کنه
    
    while True:
        try:
            for sport in SPORTS:
                logger.info(f"شروع اسکن آربیتراژ برای لیگ: {sport}")
                
                # دریافت ضرایب
                data = await asyncio.wait_for(client.fetch_odds(sport, REGIONS, MARKETS), timeout=30)
                
                if not data:
                    logger.warning(f"دیتایی برای {sport} دریافت نشد.")
                    continue
                
                if "surebets" in data:
                    last_success = datetime.utcnow()
                    count = len(data["surebets"])
                    logger.info(f"{count} سیگنال واقعی پیدا شد — پردازش شروع شد")
                    for arb in data["surebets"]:  # پردازش تمام سیگنال‌ها
                        event_name = arb["event"]["name"]
                        if is_blacklisted_event(event_name):
                            logger.info(f"رویداد بلاک‌لیست — رد شد: {event_name}")
                            continue
                        
                        signal_data = await build_signal(arb, BANKROLL, "surebet")
                        if signal_data:
                            # Double Check Verification
                            is_verified = await verify_odds_before_alert(signal_data, client, sport)
                            if not is_verified:
                                continue
                                
                            signal_data["sport"] = sport
                            await save_signal_to_redis(signal_data)
                            
                            # ذخیره در فایل برای Machine Learning
                            try:
                                ArbitragePredictor.save_real_signal(signal_data)
                            except Exception as e:
                                logger.error(f"Error saving ML data: {e}")
                                
                            success = await send_surebet_alert(signal_data)
                            if success:
                                logger.success(f"سیگنال واقعی ارسال شد: {event_name} — {signal_data['profit_pct']}%")
                                
                                # فاز ۳: ثبت CLV و اضافه کردن تعداد شرط‌ها در Health Monitor
                                for leg in signal_data["legs"]:
                                    await health_monitor.increment_daily_bet_count(leg["bookie"])
                                    await clv_tracker.record_bet_placement(
                                        odd_taken=float(leg["odd"]),
                                        event_id=signal_data["id"],
                                        market=leg["selection"],
                                        bookmaker=leg["bookie"]
                                    )
                                    
                            await asyncio.sleep(random.uniform(2, 5))  # رفتار انسانی
            
            logger.info(f"پایان دور اسکن تمام لیگ‌ها. توقف برای {FETCH_INTERVAL} ثانیه...")
            await asyncio.sleep(FETCH_INTERVAL)  # دقیقاً ۶۰ ثانیه صبر کن
            
        except Exception as e:
            logger.error(f"خطای غیرمهم (ادامه می‌دیم): {e}")
            await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())