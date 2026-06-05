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
from tracking.db_session import engine
from tracking.models import Base, ArbitrageOpportunity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

log = structlog.get_logger()

# ورزش‌ها و مارکت‌هایی که اسکن می‌شوند
SCAN_CONFIG = [
    {"sport_key": "soccer_italy_serie_a",       "markets": ["h2h", "totals"]},
    {"sport_key": "soccer_uefa_champs_league",   "markets": ["h2h", "totals"]},
    {"sport_key": "basketball_euroleague",       "markets": ["h2h", "totals"]},
    {"sport_key": "tennis_atp",                  "markets": ["h2h"]},
]

async def scan_loop(pipeline: FilterPipeline, fetcher: OddsFetcher,
                    calculator: ArbCalculator, notifier: TelegramNotifier,
                    steam_detector: SteamDetector, clv_tracker: CLVTracker,
                    ml_collector: MLCollector, stake_calc: StakeCalculator,
                    vig_remover: VigRemover, exposure_controller: ExposureController):
    """
    حلقه اصلی اسکن — بی‌وقفه اجرا می‌شود.
    هر SCAN_INTERVAL_SECONDS ثانیه یک دور کامل می‌زند.
    """
    while True:
        try:
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
                        # ذخیره در دیتابیس
                        async with async_session() as db:
                            new_opp = ArbitrageOpportunity(
                                event_id=opp.get('event_id', 'unknown'),
                                sport_key=opp.get('sport_key', 'unknown'),
                                profit_pct=opp.get('profit_pct', 0.0),
                                quality=opp.get('quality', {}).get('quality', 'UNKNOWN'),
                                is_steamed=False # اگر به اینجا رسیده یعنی steam نبوده
                            )
                            db.add(new_opp)
                            await db.commit()
                        
                        await notifier.send_arbitrage_alert(result)
                    
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
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
        listener = TelegramListener()
        dashboard = Dashboard(health_monitor, clv_tracker, redis_client)
        
        # اجرای هم‌زمان scan loop و داشبورد و لیسنر تلگرام
        await asyncio.gather(
            scan_loop(pipeline, fetcher, calculator, notifier,
                      steam_detector, clv_tracker, ml_collector, stake_calc, vig_remover, exposure),
            dashboard.start_server(),
            listener.start_polling(),
            return_exceptions=True
        )


if __name__ == "__main__":
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(10))
    asyncio.run(main())