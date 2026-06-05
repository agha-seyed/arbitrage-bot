import structlog
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes
from config import settings
import redis.asyncio as aioredis
from tracking.ml_collector import MLCollector
from tracking.db_session import engine
from tracking.models import ArbitrageOpportunity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

log = structlog.get_logger()

class TelegramListener:
    """
    گوش دادن به دکمه‌های شیشه‌ای تلگرام.
    باید به عنوان یک تسک در پس‌زمینه (مثلا در main.py) اجرا شود.
    """
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ml_collector = MLCollector()
        
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """زمانی که کاربر روی یکی از دکمه‌ها کلیک کند این تابع اجرا می‌شود."""
        query = update.callback_query
        await query.answer()  # متوقف کردن حالت لودینگ دکمه
        
        data = query.data
        if data.startswith("bet_placed_"):
            event_id = data.replace("bet_placed_", "")
            log.info("user_interaction", action="bet_placed", event_id=event_id)
            
            # ذخیره تعامل کاربر برای آموزش ماشین
            await self._record_interaction(event_id, "PLACED")
            
            # تغییر متن پیام برای اینکه کاربر بداند ثبت شده است
            await query.edit_message_reply_markup(reply_markup=None)
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ <b>ثبت شد:</b> شما اعلام کردید این شرط را بسته‌اید.", parse_mode="HTML")
            
        elif data.startswith("bet_missed_"):
            event_id = data.replace("bet_missed_", "")
            log.info("user_interaction", action="bet_missed", event_id=event_id)
            
            await self._record_interaction(event_id, "MISSED")
            
            await query.edit_message_reply_markup(reply_markup=None)
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ <b>رد شد:</b> مارکت بسته بود یا فرصت از دست رفت.", parse_mode="HTML")

    async def _record_interaction(self, event_id: str, status: str):
        # در دیتابیس Redis رکورد می‌کنیم که کاربر چه واکنشی نشان داد
        key = f"interaction:{event_id}"
        await self.redis.set(key, status, ex=86400 * 30) # نگه داشتن برای یک ماه
        
        # ذخیره در دیتابیس SQL
        try:
            async with async_session() as db:
                stmt = select(ArbitrageOpportunity).where(ArbitrageOpportunity.event_id == event_id)
                result = await db.execute(stmt)
                opp = result.scalar_one_or_none()
                if opp:
                    opp.user_status = status
                    await db.commit()
                    log.info("db_interaction_saved", event_id=event_id, status=status)
        except Exception as e:
            log.error("db_interaction_error", error=str(e))
        
    async def start_polling(self):
        """اجرای سرور پولینگ تلگرام"""
        if not settings.TELEGRAM_BOT_TOKEN:
            log.error("telegram_token_missing")
            return
            
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        log.info("telegram_listener_started")
        # Initialize and start the application manually so it doesn't block the main event loop
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
