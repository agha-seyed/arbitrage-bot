from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import structlog
import uuid

log = structlog.get_logger()

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, text: str) -> bool:
        if not self.bot.token or not self.chat_id:
            return False
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="Markdown")
            return True
        except Exception as e:
            log.error("telegram_send_msg_failed", error=str(e))
            return False

    async def send_arbitrage_alert(self, opportunity: dict, active_users: dict = None) -> int:
        """
        سیگنال را با دکمههای Win/Loss ارسال کن.
        ابتدا به ادمین می‌فرستد تا message_id بگیرد، سپس برای بقیه برودکست می‌کند.
        مقدار برگشتی: message_id تلگرام (برای ذخیره در دیتابیس)
        """
        if not self.bot.token or not self.chat_id:
            log.warning("telegram_not_configured")
            return 0

        text = self._format_signal_text(opportunity)

        placeholder = "PENDING"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Win",  callback_data=f"win:{placeholder}"),
                InlineKeyboardButton("❌ Loss", callback_data=f"loss:{placeholder}"),
            ],
            [
                InlineKeyboardButton("⚠️ Void", callback_data=f"void:{placeholder}"),
                InlineKeyboardButton("⏭ Skip",  callback_data=f"skip:{placeholder}"),
            ]
        ])

        try:
            msg = await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            real_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Win",  callback_data=f"win:{msg.message_id}"),
                    InlineKeyboardButton("❌ Loss", callback_data=f"loss:{msg.message_id}"),
                ],
                [
                    InlineKeyboardButton("⚠️ Void", callback_data=f"void:{msg.message_id}"),
                    InlineKeyboardButton("⏭ Skip",  callback_data=f"skip:{msg.message_id}"),
                ]
            ])
            await self.bot.edit_message_reply_markup(
                chat_id=self.chat_id,
                message_id=msg.message_id,
                reply_markup=real_keyboard
            )
            
            # برودکست برای بقیه کاربران فعال
            if active_users:
                for uid in active_users.keys():
                    if str(uid) == str(self.chat_id):
                        continue
                    try:
                        await self.bot.send_message(
                            chat_id=uid,
                            text=text,
                            reply_markup=real_keyboard,
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        log.error("telegram_broadcast_alert_failed", chat_id=uid, error=str(e))

            return msg.message_id
        except Exception as e:
            log.error("telegram_alert_failed", error=str(e))
            return 0

    def _format_signal_text(self, opportunity: dict) -> str:
        """فرمت پیام تلگرام"""
        quality = opportunity.get('quality', {})
        urgency = opportunity.get('urgency', {})
        legs = opportunity.get('legs', [])

        lines = [
            f"{urgency.get('emoji','📊')} *{urgency.get('label','SIGNAL')}*",
            f"",
            f"🎯 *{opportunity.get('event_name', '')}*",
            f"💰 سود تضمینی: `{opportunity.get('profit_pct', 0.0):.2f}%`",
            f"🏆 کیفیت: {quality.get('emoji','')} {quality.get('quality','')}",
            f"",
        ]

        for i, leg in enumerate(legs, 1):
            lines.append(
                f"شرط {i}: *{leg.get('bookmaker','')}* → "
                f"`{leg.get('verified_odd', leg.get('odd',0)):.2f}` "
                f"({leg.get('stake',0):.0f}€)"
            )

        if urgency.get('note'):
            lines.append(f"\n⚡ {urgency['note']}")

        return "\n".join(lines)
