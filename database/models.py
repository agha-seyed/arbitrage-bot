from sqlalchemy import Column, String, Float, Integer, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
import enum

class Base(DeclarativeBase):
    pass

class SignalStatus(str, enum.Enum):
    PENDING   = "pending"    # ارسال شده، منتظر بازخورد کاربر
    WIN       = "win"        # کاربر برنده شد
    LOSS      = "loss"       # کاربر بازنده شد
    VOID      = "void"       # شرط باطل شد
    SKIPPED   = "skipped"    # کاربر رد کرد

class ArbitrageSignal(Base):
    """
    هر آربیتراژی که از pipeline رد شد و به تلگرام ارسال شد اینجا ذخیره میشود.
    telegram_message_id برای پیدا کردن پیام هنگام دریافت بازخورد استفاده میشود.
    """
    __tablename__ = "arbitrage_signals"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    event_id          = Column(String(100), nullable=False, index=True)
    event_name        = Column(String(200), nullable=False)
    sport_key         = Column(String(60), nullable=False)
    commence_time     = Column(DateTime(timezone=True), nullable=False)

    # ضرایب و سود
    profit_pct        = Column(Float, nullable=False)
    bookmaker_1       = Column(String(60), nullable=False)
    bookmaker_2       = Column(String(60), nullable=False)
    odd_1             = Column(Float, nullable=False)
    odd_2             = Column(Float, nullable=False)
    stake_1           = Column(Float, nullable=False)
    stake_2           = Column(Float, nullable=False)

    # کیفیت سیگنال
    quality           = Column(String(10), nullable=False)   # HIGH / MEDIUM
    urgency_label     = Column(String(20), nullable=True)    # PREMIUM / URGENT / ...

    # نتیجه و پیگیری
    status            = Column(Enum(SignalStatus), default=SignalStatus.PENDING, nullable=False)
    telegram_message_id = Column(Integer, nullable=True, index=True)

    # CLV
    clv_value         = Column(Float, nullable=True)         # بعداً پر میشود
    closing_odd_1     = Column(Float, nullable=True)
    closing_odd_2     = Column(Float, nullable=True)

    # زمانها
    detected_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at       = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_name": self.event_name,
            "profit_pct": self.profit_pct,
            "bookmaker_1": self.bookmaker_1,
            "bookmaker_2": self.bookmaker_2,
            "odd_1": self.odd_1,
            "odd_2": self.odd_2,
            "stake_1": self.stake_1,
            "stake_2": self.stake_2,
            "quality": self.quality,
            "status": self.status.value,
            "clv_value": self.clv_value,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }
