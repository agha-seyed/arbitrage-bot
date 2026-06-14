import asyncio
import aiohttp
import redis.asyncio as aioredis
import structlog
from config import settings

from core.odds_fetcher import OddsFetcher
from core.arb_calculator import ArbCalculator
from core.stake_calculator import StakeCalculator
from core.vig_remover import VigRemover

from filters.odds_verifier import OddsVerifier
from filters.profit_filter import DynamicProfitFilter
from filters.bookmaker_classifier import BookmakerClassifier
from filters.steam_detector import SteamDetector
from filters.pipeline import FilterPipeline

from protection.account_health import AccountHealthMonitor
from protection.exposure_control import ExposureController
from protection.bankroll_manager import BankrollManager

from tracking.clv_tracker import CLVTracker
from tracking.ml_collector import MLCollector

from output.telegram_notifier import TelegramNotifier
from output.telegram_listener import TelegramListener
from output.dashboard import Dashboard

from database.db_session import init_db, save_signal

log = structlog.get_logger()

# ورزش‌ها و مارکت‌هایی که اسکن می‌شوند
SCAN_CONFIG = [
    {"sport_key": "upcoming",                      "markets": ["h2h"]},
    {"sport_key": "soccer_fifa_world_cup",         "markets": ["h2h", "totals"]},
    {"sport_key": "soccer_china_superleague",      "markets": ["h2h", "totals"]},
    {"sport_key": "baseball_mlb",                  "markets": ["h2h", "totals"]},
]
import random
from output.telegram_listener import TelegramListener

async def status_notifier_loop(notifier: TelegramNotifier, tg_listener: TelegramListener):
    """هر 60 ثانیه یک پیام وضعیت به کانال می‌فرستد."""
    messages = [
        "🔍 {name} عزیز، ربات با قدرت در حال اسکن زنده بازارهای جهانی است...",
        "⏳ می‌دونم منتظری! من هنوز بیدارم و دارم بازار رو اسکن می‌کنم...",
        "🕵️‍♂️ باز هم دارم می‌گردم! گوشه به گوشه سایت‌ها رو زیر و رو می‌کنم تا یه آربیتراژ ناب پیدا کنم...",
        "⚡ شکارچی ویرانگران بیداره و داره ضرایب رو مقایسه می‌کنه...",
        "👀 {name} عزیز، حواسم به همه‌چیز هست، به محض پیدا کردن سود خبرت می‌کنم!"
    ]
    while True:
        await asyncio.sleep(60)
        if not tg_listener.is_paused:
            msg_template = random.choice(messages)
            
            # ارسال پیام به ادمین (دیفالت)
            admin_msg = msg_template.replace("{name}", getattr(tg_listener, 'admin_name', 'ادمین'))
            await notifier.send_message(admin_msg)
            
            # ارسال پیام به سایر کاربرانی که /start زده‌اند
            for chat_id, name in tg_listener.active_users.items():
                # اگر کاربر همان ادمین دیفالت بود، دوباره ارسال نشود
                if str(chat_id) == str(notifier.chat_id):
                    continue
                
                user_msg = msg_template.replace("{name}", name)
                try:
                    await notifier.bot.send_message(chat_id=chat_id, text=user_msg)
                except Exception as e:
                    log.error("broadcast_error", chat_id=chat_id, error=str(e))

async def scan_loop(pipeline: FilterPipeline, fetcher: OddsFetcher,
                    calculator: ArbCalculator, notifier: TelegramNotifier,
                    steam_detector: SteamDetector, clv_tracker: CLVTracker,
                    ml_collector: MLCollector, stake_calc: StakeCalculator,
                    vig_remover: VigRemover, exposure_controller: ExposureController,
                    tg_listener: TelegramListener):
    """
    حلقه اصلی اسکن — بی‌وقفه اجرا می‌شود.
    هر SCAN_INTERVAL_SECONDS ثانیه یک دور کامل می‌زند.
    """
    while True:
        try:
            if tg_listener.is_paused:
                await asyncio.sleep(5)
                continue

            for config in SCAN_CONFIG:
                odds_data = await fetcher.get_odds(
                    sport_key=config['sport_key'],
                    markets=",".join(config['markets'])
                )
                
                if odds_data is None:
                    log.warning("no_data", sport=config['sport_key'])
                    continue
                
                # ثبت همه ضرایب در SteamDetector (قبل از محاسبه)
                for event in odds_data:
                    for bm in event.get('bookmakers', []):
                        for mkt in bm.get('markets', []):
                            for out in mkt.get('outcomes', []):
                                await steam_detector.record_odd(
                                    event['id'], bm['key'], mkt['key'], out['price']
                                )
                
                # پیدا کردن آربیتراژها
                opportunities = calculator.find_all(odds_data)
                
                for opp in opportunities:
                    # محاسبه Stakes
                    opp = stake_calc.calculate(opp)
                    if 'stakes_calculated' not in opp:
                        # اگر به دلیل کم بودن سرمایه باطل شده بود
                        continue
                        
                    # اکسپوژر کنترل (بعد از محاسبه stake باید چک شود)
                    can_place = True
                    for leg in opp['legs']:
                        if not await exposure_controller.can_place(leg['bookmaker'], leg['stake']):
                            can_place = False
                            break
                    if not can_place:
                        continue
                        
                    # حذف حاشیه سود برای محاسبه ضریب واقعی
                    opp = vig_remover.calculate_true_odds(opp)
                    
                    # اجرای pipeline فیلترها
                    approved, result = await pipeline.run(opp)
                    
                    if not approved:
                        ml_collector.record_rejected(opp, result['reason'])
                        continue
                        
                    # اگر از فیلترها با موفقیت رد شد، حالا record_placement برای اکسپوژر فراخوانی شود
                    for leg in result['legs']:
                        await exposure_controller.record_placement(leg['bookmaker'], leg['stake'])
                    
                    # ثبت برای CLV
                    clv_tracker.record_placement(result)
                    
                    # ذخیره برای ML
                    ml_collector.record_approved(result)
                    
                    # ارسال به تلگرام
                    if approved:
                        telegram_msg_id = await notifier.send_arbitrage_alert(result, getattr(tg_listener, 'active_users', None))
                        if telegram_msg_id > 0:
                            await save_signal(result, telegram_msg_id)
                    
                    log.info(
                        "signal_sent",
                        event=result.get('event_name'),
                        profit=result['profit_pct'],
                        quality=result['quality']['quality'],
                        urgency=result['urgency']['label']
                    )
        
        except Exception as e:
            log.error("scan_loop_error", error=str(e), exc_info=True)
        
        await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)


async def main():
    log.info("bot_starting", version="GOD_MODE_v9.0_ENTERPRISE")
    
    # ساخت جداول دیتابیس
    await init_db()
    
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    
    async with aiohttp.ClientSession() as session:
        # ساخت تمام ماژول‌ها
        fetcher = OddsFetcher(session)
        calculator = ArbCalculator()
        stake_calc = StakeCalculator()
        vig_remover = VigRemover()
        bankroll = BankrollManager(redis_client)
        
        verifier = OddsVerifier(fetcher)
        profit_filter = DynamicProfitFilter()
        classifier = BookmakerClassifier()
        steam_detector = SteamDetector(redis_client)
        health_monitor = AccountHealthMonitor(redis_client)
        exposure = ExposureController(redis_client)
        
        pipeline = FilterPipeline(
            verifier=verifier,
            profit_filter=profit_filter,
            classifier=classifier,
            steam_detector=steam_detector,
            health_monitor=health_monitor,
            exposure_controller=exposure
        )
        
        clv_tracker = CLVTracker(redis_client)
        ml_collector = MLCollector()
        notifier = TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID)
        
        # ۳. ساخت telegram listener
        tg_listener = TelegramListener()
        
        dashboard = Dashboard(health_monitor, clv_tracker, redis_client)
        
        # ارسال پیام شروع به تلگرام
        await notifier.send_message("🚀 ربات آربیتراژ ویرانگران با موفقیت روشن شد و در حال اسکن بازار است!")

        # اجرای هم‌زمان scan loop و داشبورد و لیسنر تلگرام
        
        async def run_with_restart(coro_func, *args, **kwargs):
            while True:
                try:
                    await coro_func(*args, **kwargs)
                except Exception as e:
                    log.error("task_crashed_restarting", task=coro_func.__name__, error=str(e), exc_info=True)
                    await asyncio.sleep(5)

        results = await asyncio.gather(
            run_with_restart(scan_loop, pipeline, fetcher, calculator, notifier, steam_detector, clv_tracker, ml_collector, stake_calc, vig_remover, exposure, tg_listener),
            run_with_restart(status_notifier_loop, notifier, tg_listener),
            run_with_restart(dashboard.start_server),
            run_with_restart(tg_listener.start),
            return_exceptions=True
        )
        
        for r in results:
            if isinstance(r, Exception):
                log.error("gather_task_crashed_fatally", error=str(r), exc_info=r)

if __name__ == "__main__":
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(10))
    asyncio.run(main())