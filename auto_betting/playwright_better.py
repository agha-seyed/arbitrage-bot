"""
هشدار: این ماژول با ریسک بالا است.
فقط وقتی تمام تستها OK بودند فعالش کن.
ENABLE_AUTO_BETTING=false در .env باشد مگر آنکه مطمئن باشی.
"""

import asyncio
import random
import json
from playwright.async_api import async_playwright, Browser, BrowserContext
from config import settings
import structlog

log = structlog.get_logger()

class ProxyManager:
    """
    لیست پروکسیهای residential ایتالیایی را مدیریت میکند.
    هر بار که یک اکانت وارد سایت میشود، یک پروکسی تصادفی انتخاب میشود.
    """

    def __init__(self, proxy_list: list[dict]):
        """
        proxy_list: لیستی از دیکشنریها با کلیدهای:
            server: "http://host:port"
            username: "..."
            password: "..."
        """
        self._proxies = proxy_list
        self._used_count = {i: 0 for i in range(len(proxy_list))}

    def get_proxy(self) -> dict:
        """
        کماستفادهترین پروکسی را برگردان.
        اگر لیست خالی بود، None برگردان (بدون پروکسی).
        """
        if not self._proxies:
            return None

        # انتخاب پروکسی با کمترین استفاده + کمی تصادفی
        min_count = min(self._used_count.values())
        candidates = [i for i, c in self._used_count.items() if c <= min_count + 1]
        chosen_idx = random.choice(candidates)
        self._used_count[chosen_idx] += 1
        return self._proxies[chosen_idx]

class SafeBrowserSession:
    """
    یک session مرورگر با fingerprint انسانی.
    هر اکانت باید session مجزا داشته باشد.
    """

    # fingerprintهای واقعی از مرورگرهای ایتالیایی
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    VIEWPORTS = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
    ]

    def __init__(self, proxy_manager: ProxyManager, account_id: str):
        self.proxy_manager = proxy_manager
        self.account_id = account_id
        self._browser: Browser = None
        self._context: BrowserContext = None

    async def __aenter__(self):
        proxy = self.proxy_manager.get_proxy()
        user_agent = random.choice(self.USER_AGENTS)
        viewport = random.choice(self.VIEWPORTS)

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ]
        )

        context_options = {
            "user_agent": user_agent,
            "viewport": viewport,
            "locale": "it-IT",
            "timezone_id": "Europe/Rome",
            "storage_state": f"sessions/{self.account_id}.json"
                             if self._session_exists() else None,
        }

        if proxy:
            context_options["proxy"] = proxy
            log.info("using_proxy", account=self.account_id, server=proxy['server'])

        self._context = await self._browser.new_context(**context_options)

        # مخفی کردن از Cloudflare و سیستمهای ضدربات
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['it-IT', 'it', 'en'] });
        """)

        return self._context

    async def __aexit__(self, *args):
        # ذخیره session برای دفعه بعد (لاگین نشود)
        try:
            import os
            os.makedirs("sessions", exist_ok=True)
            await self._context.storage_state(path=f"sessions/{self.account_id}.json")
        except Exception:
            pass

        await self._context.close()
        await self._browser.close()
        await self._pw.stop()

    def _session_exists(self) -> bool:
        import os
        return os.path.exists(f"sessions/{self.account_id}.json")

    @staticmethod
    async def human_delay(min_ms: int = 600, max_ms: int = 2200):
        """تأخیر تصادفی — هیچوقت بدون این کلیک نزن"""
        await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

    @staticmethod
    async def human_type(page, selector: str, text: str):
        """تایپ آهسته شبیه انسان"""
        await page.click(selector)
        await asyncio.sleep(random.uniform(0.2, 0.5))
        for char in text:
            await page.type(selector, char)
            await asyncio.sleep(random.uniform(0.05, 0.15))


class SnaiAutoBetter:
    """
    مثال پیادهسازی برای سایت Snai.
    برای هر سایت دیگر، یک کلاس مجزا بساز.

    مهم: selectors باید با بررسی HTML واقعی سایت تکمیل شوند.
    """

    BASE_URL = "https://www.snai.it"

    def __init__(self, proxy_manager: ProxyManager, account_id: str):
        self.proxy_manager = proxy_manager
        self.account_id = account_id

    async def place_bet(self, event_name: str, outcome: str, odd: float, stake: float) -> bool:
        """
        شرط را در سایت ثبت کن.
        True = موفق، False = خطا
        """
        if not settings.ENABLE_AUTO_BETTING:
            log.info("auto_betting_disabled", account=self.account_id)
            return False

        async with SafeBrowserSession(self.proxy_manager, self.account_id) as context:
            page = await context.new_page()

            try:
                # ۱. رفتن به صفحه بازی
                await page.goto(f"{self.BASE_URL}/sport/calcio", wait_until="networkidle")
                await SafeBrowserSession.human_delay(800, 1500)

                # ۲. جستجوی بازی
                # TODO: selector واقعی را با بررسی HTML سایت پر کن
                # await page.click("[data-testid='search-button']")
                # await SafeBrowserSession.human_type(page, "[data-testid='search-input']", event_name)

                # ۳. کلیک روی ضریب
                # TODO: پیدا کردن ضریب از بین لیست بازیها
                # odd_button = page.locator(f"[data-odd='{odd}']").first
                # await SafeBrowserSession.human_delay(400, 900)
                # await odd_button.click()

                # ۴. وارد کردن مبلغ در betslip
                # await SafeBrowserSession.human_delay(600, 1200)
                # await SafeBrowserSession.human_type(page, "[data-testid='stake-input']", str(stake))

                # ۵. بررسی ضریب قبل از تایید
                # current_odd_text = await page.locator("[data-testid='betslip-odd']").text_content()
                # if abs(float(current_odd_text) - odd) / odd > 0.02:
                #     log.warning("odd_changed_in_betslip", expected=odd, got=current_odd_text)
                #     await page.click("[data-testid='close-betslip']")
                #     return False

                # ۶. تایید نهایی
                # await SafeBrowserSession.human_delay(500, 1000)
                # await page.click("[data-testid='confirm-bet']")

                log.info("bet_placed_successfully",
                         account=self.account_id,
                         event=event_name,
                         outcome=outcome,
                         odd=odd,
                         stake=stake)
                return True

            except Exception as e:
                log.error("auto_bet_failed",
                          account=self.account_id,
                          event=event_name,
                          error=str(e))
                return False
