# 🤖 Arbitrage Bot (God Mode v9.0 Enterprise)

[🇮🇷 فارسی (Persian)](#فارسی-persian) | [🇬🇧 English](#english)

---

<a name="english"></a>
## 🇬🇧 English

Welcome to the **Arbitrage Bot (God Mode v9.0 Enterprise)** repository! This is a state-of-the-art sports betting arbitrage bot built with Python. It is designed to automatically find, verify, and execute risk-free arbitrage opportunities across various bookmakers.

### ✨ Key Features

- **Multi-Market Support:** Advanced arbitrage calculation for `H2H` (Match Winner), `Totals` (Over/Under), and `Spreads` (Asian Handicap).
- **Stealth Auto-Betting:** Integrated with Playwright and stealth plugins. It features a `ProxyManager` for IP rotation to bypass bookmaker detection systems and Cloudflare.
- **Smart Filtering Pipeline:**
  - **Odds Verifier:** Double-checks odds in real-time before betting.
  - **Steam Detector:** Uses Redis to track odds history and avoids "steaming" markets (sudden odds drops indicating a trap).
  - **Profit Filter:** Dynamically adjusts the acceptable profit margin based on the time remaining to the event.
  - **Bookmaker Classifier:** Prevents betting between two "Sharp" bookmakers to avoid bans.
- **Protection Systems:** 
  - **Exposure Control:** Limits daily wagered volume per bookmaker.
  - **Account Health:** Simulates and calculates a health score (0-100) for your accounts based on win/loss ratios and volumes.
- **Machine Learning & Database:** Fully integrated with an async SQL Database (PostgreSQL/SQLite) and a CLV (Closing Line Value) tracker. It logs all bets and user interactions for future Random Forest ML training.
- **Wall-Street UI Dashboard:** A stunning Glassmorphism & Dark Mode web dashboard powered by FastAPI, WebSocket, and Chart.js for real-time monitoring.
- **Interactive Telegram Bot:** Receive instant alerts and use inline buttons to mark bets as won/lost/voided, instantly updating the SQL database.

### 🚀 Getting Started

1. **Clone the repository**
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt aiosqlite
   ```
3. **Configure Environment:** Copy `.env.example` to `.env` and fill in your API keys (The-Odds-API, Telegram token, etc.).
4. **Run the Bot:**
   ```bash
   python main.py
   ```
5. **Access Dashboard:** Open your browser and go to `http://localhost:8080`

---

<a name="فارسی-persian"></a>
## 🇮🇷 فارسی (Persian)

به مخزن **ربات آربیتراژ (نسخه God Mode v9.0 Enterprise)** خوش آمدید! این یک ربات آربیتراژ ورزشی فوق‌پیشرفته است که با پایتون نوشته شده و به صورت خودکار فرصت‌های آربیتراژ (بدون ریسک) را بین سایت‌های شرط‌بندی پیدا کرده، تایید می‌کند و (در صورت نیاز) ثبت می‌کند.

### ✨ ویژگی‌های کلیدی

- **پشتیبانی از بازارهای پیچیده:** محاسبه پیشرفته آربیتراژ برای مارکت‌های `H2H` (برد/مساوی/باخت)، `Totals` (گل بالا/پایین) و `Spreads` (هندیکپ آسیایی).
- **شرط‌بندی اتوماتیک مخفی (Stealth):** یکپارچه شده با Playwright به همراه پلاگین مخفی‌سازی. این سیستم دارای مدیریت چرخش پروکسی (`ProxyManager`) است تا سیستم‌های امنیتی و کلودفلر (Cloudflare) را دور بزند.
- **خط لوله فیلترینگ هوشمند:**
  - **تاییدکننده ضریب (Odds Verifier):** بررسی مجدد و لحظه‌ای ضرایب قبل از شرط‌بندی.
  - **تشخیص تله‌های افت ضریب (Steam Detector):** استفاده از دیتابیس Redis برای ردیابی تاریخچه ضرایب و جلوگیری از ورود به ضرایبی که دچار افت شدید شده‌اند.
  - **فیلتر پویای سود (Profit Filter):** تنظیم هوشمند درصد سود قابل قبول بر اساس زمان باقیمانده تا شروع مسابقه.
  - **طبقه‌بندی سایت‌ها (Classifier):** جلوگیری از شرط‌بندی همزمان روی دو سایت Sharp (حرفه‌ای) برای جلوگیری از مسدود شدن اکانت.
- **سیستم‌های حفاظتی:**
  - **کنترل حجم (Exposure Control):** محدود کردن حجم پول در گردش روزانه روی هر بوکمیکر.
  - **سلامت اکانت (Account Health):** محاسبه امتیاز سلامت (۰ تا ۱۰۰) برای اکانت‌های شما بر اساس حجم و تعداد برد/باخت برای جلوگیری از لیمیت شدن.
- **یادگیری ماشین و دیتابیس:** یکپارچه‌سازی کامل با دیتابیس Async SQL (PostgreSQL/SQLite). دارای سیستم ردیابی CLV (ارزش ضریب هنگام شروع بازی) برای ذخیره تمام داده‌ها جهت آموزش هوش مصنوعی در آینده.
- **داشبورد حرفه‌ای (Wall-Street UI):** یک پنل وب فوق‌العاده زیبا با طراحی Glassmorphism و تم تاریک. دارای اتصال WebSocket و Chart.js برای نمایش نوتیفیکیشن‌ها و آمار زنده.
- **ربات تعاملی تلگرام:** ارسال فوری آلارم‌ها به همراه دکمه‌های شیشه‌ای برای ثبت نتیجه شرط (برد/باخت) و آپدیت مستقیم دیتابیس.

### 🚀 راهنمای راه‌اندازی

۱. **دانلود کدها**
۲. **نصب پیش‌نیازها:**
   ```bash
   pip install -r requirements.txt aiosqlite
   ```
۳. **تنظیمات:** فایل `.env.example` را به `.env` تغییر نام دهید و کلیدهای خود (مانند API Key و توکن تلگرام) را در آن وارد کنید.
۴. **اجرای ربات:**
   ```bash
   python main.py
   ```
۵. **مشاهده داشبورد:** مرورگر خود را باز کرده و به آدرس `http://localhost:8080` بروید.
