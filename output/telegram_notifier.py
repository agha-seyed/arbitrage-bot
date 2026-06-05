from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import structlog
import uuid

log = structlog.get_logger()

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        
    async def send_arbitrage_alert(self, opportunity: dict):
        """
        ارسال پیام به تلگرام به همراه دکمه‌های تعاملی برای ثبت نتیجه.
        """
        if not self.bot.token or not self.chat_id:
            log.warning("telegram_not_configured")
            return
            
        try:
            urgency = opportunity.get('urgency', {})
            emoji = urgency.get('emoji', '📊')
            label = urgency.get('label', 'NORMAL')
            
            quality = opportunity.get('quality', {})
            q_emoji = quality.get('emoji', '🟢')
            q_label = quality.get('quality', 'HIGH')
            
            msg = f"{emoji} <b>Arbitrage Found!</b> [{label}]\n"
            msg += f"🏆 <b>Match:</b> {opportunity['event_name']}\n"
            msg += f"💰 <b>Profit:</b> {opportunity['profit_pct']:.2f}%\n"
            msg += f"🛡️ <b>Quality:</b> {q_emoji} {q_label}\n"
            msg += f"💶 <b>Total Stake:</b> €{opportunity.get('total_stake', 0)}\n\n"
            
            for leg in opportunity['legs']:
                msg += f"🔹 <b>{leg['bookmaker']}</b> ({leg['market']}): {leg['outcome']} @ {leg['odd']} ➡️ Stake: €{leg.get('stake', 0)}\n"
            
            # شناسه یکتا برای این سیگنال ایجاد می‌کنیم تا در دیتابیس قابل رهگیری باشد
            event_id = opportunity.get('event_id', uuid.uuid4().hex[:8])
            
            # ایجاد دکمه‌های شیشه‌ای
            keyboard = [
                [
                    InlineKeyboardButton("✅ شرط بسته شد", callback_data=f"bet_placed_{event_id}"),
                    InlineKeyboardButton("❌ مارکت بسته بود", callback_data=f"bet_missed_{event_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
                
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as e:
            log.error("telegram_send_error", error=str(e))
