from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from database.db_session import update_signal_status
from database.models import SignalStatus
from config import settings
import structlog

log = structlog.get_logger()

class TelegramListener:
    """
    این کلاس موازی با telegram_notifier کار میکند.
    notifier سیگنال ارسال میکند، listener بازخورد دریافت میکند.

    فرمت callback_data دکمهها:
    "win:{telegram_message_id}"
    "loss:{telegram_message_id}"
    "void:{telegram_message_id}"
    "skip:{telegram_message_id}"
    """

    def __init__(self):
        self.app = (
            Application.builder()
            .token(settings.TELEGRAM_BOT_TOKEN)
            .build()
        )
        self._register_handlers()

    def _register_handlers(self):
        self.app.add_handler(CallbackQueryHandler(self._handle_button))
        self.app.add_handler(CommandHandler("stats", self._handle_stats))
        self.app.add_handler(CommandHandler("health", self._handle_health))

    async def _handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        هنگامی که کاربر روی یکی از دکمههای Win/Loss/Void/Skip کلیک میکند.
        """
        query = update.callback_query
        await query.answer()   # loading را برمیدارد

        data = query.data      # مثال: "win:12345"
        parts = data.split(":")
        if len(parts) != 2:
            return

        action, msg_id_str = parts
        try:
            msg_id = int(msg_id_str)
        except ValueError:
            return

        status_map = {
            "win":  SignalStatus.WIN,
            "loss": SignalStatus.LOSS,
            "void": SignalStatus.VOID,
            "skip": SignalStatus.SKIPPED,
        }

        status = status_map.get(action)
        if status is None:
            return

        success = await update_signal_status(msg_id, status)

        if success:
            emoji_map = {
                SignalStatus.WIN:     "✅ Win ثبت شد",
                SignalStatus.LOSS:    "❌ Loss ثبت شد",
                SignalStatus.VOID:    "⚠️ Void ثبت شد",
                SignalStatus.SKIPPED: "⏭ رد شد",
            }
            # ویرایش پیام اصلی تلگرام برای نشان دادن نتیجه
            try:
                original_text = query.message.text or ""
                await query.edit_message_text(
                    text=f"{original_text}\n\n─────\n{emoji_map[status]}",
                    reply_markup=None   # دکمهها را حذف کن
                )
            except Exception:
                pass   # اگر پیام خیلی قدیمی بود مشکلی نیست

            log.info("button_pressed", action=action, msg_id=msg_id)

    async def _handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /stats — آمار کلی"""
        from database.db_session import get_stats_for_ml
        signals = await get_stats_for_ml()

        wins   = sum(1 for s in signals if s['status'] == 'win')
        losses = sum(1 for s in signals if s['status'] == 'loss')
        voids  = sum(1 for s in signals if s['status'] == 'void')
        total  = wins + losses + voids

        win_rate = (wins / total * 100) if total > 0 else 0
        avg_profit = sum(s['profit_pct'] for s in signals) / len(signals) if signals else 0

        clv_values = [s['clv_value'] for s in signals if s.get('clv_value') is not None]
        avg_clv = sum(clv_values) / len(clv_values) if clv_values else 0

        text = (
            f"📊 *آمار کلی ربات*\n\n"
            f"✅ Win: {wins}\n"
            f"❌ Loss: {losses}\n"
            f"⚠️ Void: {voids}\n"
            f"📈 Win Rate: {win_rate:.1f}%\n"
            f"💰 میانگین سود: {avg_profit:.2f}%\n"
            f"📐 میانگین CLV: {avg_clv:.2f}%"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _handle_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور /health — سلامت اکانتها"""
        from protection.account_health import AccountHealthMonitor
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        monitor = AccountHealthMonitor(redis_client)
        scores = await monitor.get_all_scores()
        await redis_client.aclose()

        lines = ["🏥 *سلامت اکانتها*\n"]
        for book, info in sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True):
            bar = "█" * (info['score'] // 10) + "░" * (10 - info['score'] // 10)
            lines.append(f"`{book:<15}` {bar} {info['score']}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def start(self):
        """شروع polling — این را با asyncio.gather اجرا کن"""
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        log.info("telegram_listener_started")

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
