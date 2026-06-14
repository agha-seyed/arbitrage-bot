from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes
from database.db_session import update_signal_status
from database.models import SignalStatus
from config import settings
import structlog
import asyncio

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
        self.is_paused = False
        self.support_users = set()
        self.active_users = {}  # chat_id: first_name
        self.admin_name = "ادمین"
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
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("stop", self._handle_stop))
        self.app.add_handler(CommandHandler("about", self._handle_about))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.is_paused = False
        first_name = update.message.from_user.first_name
        chat_id = update.message.chat_id
        self.active_users[chat_id] = first_name
        self.admin_name = first_name
        
        keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton("📊 آمار کلی"), KeyboardButton("🏥 سلامت اکانت‌ها")],
                [KeyboardButton("🌐 داشبورد زنده", web_app=WebAppInfo(url="https://esi-sand.vercel.app/")), KeyboardButton("ℹ️ درباره ما")]
            ],
            resize_keyboard=True,
            persistent=True
        )
        
        await update.message.reply_text(f"▶️ {first_name} عزیز، ربات شکارچی ویرانگران استارت خورد و شروع به کار کرد! 🚀", reply_markup=keyboard)

    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.is_paused = True
        first_name = update.message.from_user.first_name
        chat_id = update.message.chat_id
        self.active_users[chat_id] = first_name
        self.admin_name = first_name
        await update.message.reply_text(
            f"⏸ {first_name} عزیز، تو استاپ رو زدی که ربات کار نکنه!\n"
            "الان از سود و سرمایه جا می‌مونی! 😱\n"
            "بذار ربات همیشه روشن باشه و کار کنه تا برات بگرده و سود پیدا کنه.\n\n"
            "برای شروع مجدد کافیه /start رو بزنی."
        )

    async def _handle_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        caption = (
            "💀🔥 *ربات آربیتراژ هوشمند ویرانگران* 🔥💀\n\n"
            "این ربات یک ماشین چاپ پولِ هوشمند است که با افتخار توسط *تیم ویرانگران* توسعه داده شده است.\n\n"
            "❓ *کار این ربات چیست؟*\n"
            "این ربات به صورت ثانیه‌ای هزاران ضریب را در ده‌ها سایت پیش‌بینی معتبر دنیا مقایسه می‌کند. "
            "هرجا اختلاف قیمتی پیدا کند که باعث شود شما با پوشش دادن تمام نتایجِ بازی *سود قطعی و بدون ریسک* "
            "(Arbitrage) ببرید، بلافاصله آن را شکار کرده و برای شما ارسال می‌کند!\n\n"
            "امکانات ویژه:\n"
            "✅ شناسایی خودکار اختلاف قیمت‌ها\n"
            "✅ فیلتر هوشمند برای حذف سیگنال‌های پرخطر\n"
            "✅ محاسبه دقیق مبلغ ورود برای تضمین سود\n\n"
            "ما بازار را ویران می‌کنیم تا شما سود کنید! 💸"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍💻 ارتباط با مدیر تیم", callback_data="contact_manager")],
            [
                InlineKeyboardButton("🛠 پشتیبانی فنی", callback_data="support"),
                InlineKeyboardButton("🌐 وب‌سایت ما", url="https://esi-sand.vercel.app/")
            ]
        ])
        
        photo_path = r"C:\Users\ehsan\.gemini\antigravity-ide\brain\6fa2c9bb-f4c5-49e1-aaac-d6278d576485\virangaran_team_logo_1781204770199.png"
        
        try:
            with open(photo_path, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        except Exception as e:
            log.error("send_about_failed", error=str(e))
            await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=keyboard)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        user_msg = update.message.text
        
        if user_msg == "📊 آمار کلی":
            await self._handle_stats(update, context)
            return
        elif user_msg == "🏥 سلامت اکانت‌ها":
            await self._handle_health(update, context)
            return
        elif user_msg == "ℹ️ درباره ما":
            await self._handle_about(update, context)
            return
            
        if user_id in self.support_users:
            self.support_users.remove(user_id)
            
            # Send to Telegram Admin
            try:
                await context.bot.send_message(
                    chat_id=settings.TELEGRAM_CHAT_ID,
                    text=f"🚨 *درخواست پشتیبانی جدید*\nاز طرف کاربر: `{user_id}`\n\nمتن پیام:\n{user_msg}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                log.error("telegram_support_forward_failed", error=str(e))
                
            # Send Email
            from core.email_sender import send_support_email
            await send_support_email(user_msg, str(user_id))
            
            await update.message.reply_text("✅ درخواست پشتیبانی شما با موفقیت ثبت شد و به صورت همزمان به مدیر و ایمیل پشتیبانی (agha.seyed.ehsan@gmail.com) ارسال گردید.")

    async def _handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        هنگامی که کاربر روی یکی از دکمههای شیشه‌ای کلیک میکند.
        """
        query = update.callback_query
        await query.answer()   # loading را برمیدارد

        data = query.data
        if data == "support":
            self.support_users.add(query.from_user.id)
            await query.message.reply_text("لطفاً مشکل یا درخواست فنی خود را در یک پیام کامل تایپ کنید و بفرستید:")
            return
            
        if data == "contact_manager":
            await query.message.reply_text("برای ارتباط مستقیم با مدیر تیم، لطفاً به ایمیل زیر پیام دهید:\n📧 `agha.seyed.ehsan@gmail.com`", parse_mode="Markdown")
            return

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
        
        # Block forever to prevent auto-restart loop
        self._stop_event = asyncio.Event()
        await self._stop_event.wait()

    async def stop(self):
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
