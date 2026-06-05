from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update
from database.models import Base, ArbitrageSignal, SignalStatus
from datetime import datetime, timezone
from config import settings
import structlog

log = structlog.get_logger()

# ساخت engine
# برای SQLite:   sqlite+aiosqlite:///./arbitrage.db
# برای PostgreSQL: postgresql+asyncpg://user:pass@host/db
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,          # True فقط برای debug
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """ساخت جداول اگر وجود ندارند — یک بار در startup اجرا میشود"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database_initialized")

async def save_signal(opportunity: dict, telegram_message_id: int) -> int:
    """
    یک سیگنال تایید شده را در دیتابیس ذخیره کن.
    telegram_message_id برای پیدا کردن این رکورد هنگام Win/Loss استفاده میشود.
    مقدار برگشتی: ID رکورد در دیتابیس
    """
    legs = opportunity.get('legs', [])
    leg1 = legs[0] if len(legs) > 0 else {}
    leg2 = legs[1] if len(legs) > 1 else {}

    signal = ArbitrageSignal(
        event_id            = opportunity['event_id'],
        event_name          = opportunity.get('event_name', ''),
        sport_key           = opportunity.get('sport_key', ''),
        commence_time       = datetime.fromisoformat(opportunity['commence_time']),
        profit_pct          = opportunity['profit_pct'],
        bookmaker_1         = leg1.get('bookmaker', ''),
        bookmaker_2         = leg2.get('bookmaker', ''),
        odd_1               = leg1.get('verified_odd', leg1.get('odd', 0)),
        odd_2               = leg2.get('verified_odd', leg2.get('odd', 0)),
        stake_1             = leg1.get('stake', 0),
        stake_2             = leg2.get('stake', 0),
        quality             = opportunity.get('quality', {}).get('quality', 'UNKNOWN'),
        urgency_label       = opportunity.get('urgency', {}).get('label', ''),
        telegram_message_id = telegram_message_id,
    )

    async with AsyncSessionLocal() as session:
        session.add(signal)
        await session.commit()
        await session.refresh(signal)
        log.info("signal_saved", signal_id=signal.id, event=signal.event_name)
        return signal.id

async def update_signal_status(telegram_message_id: int, status: SignalStatus) -> bool:
    """
    وقتی کاربر در تلگرام Win یا Loss میزند، این تابع فراخوانی میشود.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ArbitrageSignal)
            .where(ArbitrageSignal.telegram_message_id == telegram_message_id)
        )
        signal = result.scalar_one_or_none()

        if signal is None:
            log.warning("signal_not_found", telegram_message_id=telegram_message_id)
            return False

        signal.status      = status
        signal.resolved_at = datetime.now(timezone.utc)
        await session.commit()

        log.info("signal_status_updated",
                 signal_id=signal.id,
                 event=signal.event_name,
                 status=status.value)
        return True

async def get_stats_for_ml() -> list[dict]:
    """
    تمام سیگنالهای resolve شده را برای آموزش ML برمیگرداند.
    فقط WIN، LOSS، VOID — نه PENDING یا SKIPPED.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ArbitrageSignal)
            .where(ArbitrageSignal.status.in_([
                SignalStatus.WIN, SignalStatus.LOSS, SignalStatus.VOID
            ]))
        )
        signals = result.scalars().all()
        return [s.to_dict() for s in signals]
