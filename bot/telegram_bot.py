# bot/telegram_bot.py — اصلاح شده برای aiogram 3.13.1
import os
import asyncio
from pathlib import Path
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

# Validate ENV
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("TELEGRAM_BOT_TOKEN تعریف نشده")
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN")

try:
    CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID") or "")
except:
    logger.critical("TELEGRAM_CHAT_ID نامعتبر")
    raise SystemExit("Invalid TELEGRAM_CHAT_ID")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

SIREN_PATH = Path("assets/siren_15sec.ogg")

# اصلاح اصلی — parse_mode جدید
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

DIRECT_LINKS = {
    "snai": "https://m.snai.it/sport/calcio",
    "sisal": "https://www.sisal.it/scommesse-matchpoint/calcio",
    "eurobet": "https://www.eurobet.it/sport/calcio",
    "goldbet": "https://www.goldbet.it/scommesse/calcio",
    "better": "https://www.better.it/scommesse",
    "planetwin365": "https://www.planetwin365.it/sport",
    "betflag": "https://www.betflag.it/sport/calcio",
    "bet365_it": "https://www.bet365.it/#/AC/B1/C1/",
    "pinnacle": "https://www.pinnacle.com/en/soccer/matchups",
    "betfair_it": "https://www.betfair.it/exchange/plus/football"
}

async def send_text_fallback(signal: dict):
    prefix = "[DRY RUN] " if DRY_RUN else ""
    lines = [
        f"{prefix}SUREBET GARANTITO 2027",
        f"Match: {signal['event']}",
        f"Profitto: {signal['profit_pct']}% → €{signal['guaranteed_profit']:.1f}",
        f"Totale stake: €{signal['total_stake']}",
        "",
    ]
    for leg in signal["legs"]:
        lines.append(f"{leg['bookie'].upper()} → {leg['selection']} @ {leg['odd']} → €{leg['stake']}")
    lines.append("Meno di 60 secondi rimasti!")

    caption = "\n".join(lines)

    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=caption,
                disable_web_page_preview=True,
                protect_content=True
            )
            logger.info(f"{prefix}سیگنال متنی ارسال شد")
            return True
        except Exception as e:
            logger.warning(f"ارسال متن ناموفق: {e}")
            await asyncio.sleep(2 ** attempt)
    return False

async def send_surebet_alert(signal: dict) -> bool:
    prefix = "[DRY RUN] " if DRY_RUN else ""
    event = signal["event"]
    profit_pct = signal["profit_pct"]
    total_stake = signal["total_stake"]
    profit_eur = signal["guaranteed_profit"]
    legs = signal["legs"]

    lines = [
        f"{prefix}SUREBET GARANTITO 2027",
        f"Match: <b>{event}</b>",
        f"Profitto: <b>{profit_pct}%</b> → <b>€{profit_eur:.1f}</b>",
        f"Totale stake: <b>€{total_stake}</b>",
        "",
    ]

    for i, leg in enumerate(legs, 1):
        bookie = leg["bookie"]
        selection = leg["selection"]
        odd = leg["odd"]
        stake = leg["stake"]
        link = leg.get("link", DIRECT_LINKS.get(bookie, "#"))
        bookie_name = bookie.upper().replace("BET365_IT", "BET365")
        
        lines.append(
            f"{ '1️⃣' if i==1 else '2️⃣' if i==2 else '3️⃣' } <b>{bookie_name}</b>\n"
            f"   {selection} @ <code>{odd}</code>\n"
            f"   Stake: <b>€{stake}</b> → <a href='{link}'>APRI SUBITO</a>"
        )

    lines.extend([
        "",
        "Meno di 55 secondi rimasti!",
        "Non inoltrabile — Solo per te"
    ])

    caption = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="شرط بستم", callback_data=f"done_{signal['id']}"),
            InlineKeyboardButton(text="رد کردم", callback_data=f"skip_{signal['id']}")
        ]
    ])

    if DRY_RUN or not SIREN_PATH.exists():
        return await send_text_fallback(signal)

    for attempt in range(3):
        try:
            await bot.send_voice(
                chat_id=CHAT_ID,
                voice=InputFile(SIREN_PATH),
                caption=caption,
                protect_content=True,
                reply_markup=keyboard,
                disable_notification=False
            )
            logger.info(f"{prefix}سیگنال با صدا ارسال شد")
            return True
        except Exception as e:
            logger.warning(f"ارسال صدا ناموفق: {e}")
            await asyncio.sleep(2 ** attempt)

    return await send_text_fallback(signal)