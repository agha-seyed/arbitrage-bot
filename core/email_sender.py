import smtplib
from email.message import EmailMessage
import asyncio
import structlog
from config import settings

log = structlog.get_logger()

async def send_support_email(user_message: str, user_id: str):
    """
    ارسال ایمیل پشتیبانی به آدرس مدیر
    """
    if not settings.SMTP_SERVER or not settings.SMTP_USER or not settings.SMTP_PASS:
        log.warning("smtp_not_configured", msg="ایمیل ارسال نشد چون تنظیمات SMTP وجود ندارد.")
        return False

    def _send():
        msg = EmailMessage()
        msg.set_content(f"یک درخواست پشتیبانی از طرف کاربر با آیدی {user_id} دریافت شد:\n\n{user_message}")
        msg['Subject'] = 'درخواست پشتیبانی ربات ویرانگران'
        msg['From'] = settings.SMTP_USER
        msg['To'] = settings.ADMIN_EMAIL

        try:
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            return True
        except Exception as e:
            log.error("email_send_failed", error=str(e))
            return False

    return await asyncio.to_thread(_send)
