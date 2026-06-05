from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class ArbitrageOpportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, index=True)
    sport_key = Column(String)
    profit_pct = Column(Float)
    is_steamed = Column(Boolean, default=False)
    quality = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # کاربر در تلگرام اعلام کرده که شرط بسته یا از دست داده
    user_status = Column(String, default="PENDING")  # PLACED, MISSED
    
    # این فیلدها توسط سرویس CLVUpdater پر می‌شوند
    closing_clv = Column(Float, nullable=True)
    is_palpable_error = Column(Boolean, default=False)
