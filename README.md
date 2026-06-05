# 🚀 Italian Arbitrage Beast 2027 (GOD MODE)

ربات هوشمند و پیشرفته آربیتراژ شرط‌بندی فوتبال (و ورزش‌های دیگر) با تمرکز روی سایت‌های ایتالیایی (Snai, Sisal, Eurobet, ...).
این ربات به طور خودکار بازی‌ها را چک می‌کند، مبالغ را بر اساس Kelly Criterion و True Odds محاسبه می‌کند و در صورت سودده بودن، از طریق تلگرام با آلارم صوتی به شما اطلاع می‌دهد.

## ✨ ویژگی‌ها
- 🔍 اسکن اتوماتیک از The-Odds-API (پشتیبانی از 1X2 و Over/Under)
- 🧮 محاسبه احتمال واقعی (True Odds) و Value Betting
- 🛡️ مدیریت میزان ریسک روزانه (Daily Exposure) برای هر سایت با Redis
- 🚨 ارسال سیگنال سریع در تلگرام با فایل صوتی آلارم
- 📊 داشبورد وب زنده (FastAPI) برای مانیتورینگ سیستم
- 🐳 پشتیبانی کامل از Docker و Multi-Worker

## ⚙️ پیش‌نیازها
- Docker و Docker Compose (یا نصب Python 3.11 و Redis به صورت لوکال)
- ربات تلگرامی (ایجاد از طریق BotFather@)
- کلید API رایگان از سایت [The-Odds-API](https://the-odds-api.com/)

## 🚀 راه‌اندازی با Docker (پیشنهادی)

۱. ریپازیتوری را کلون کنید:
```bash
git clone https://github.com/agha-seyed/arbitrage-bot.git
cd arbitrage-bot
```

۲. فایل `.env.example` را کپی کرده و نام آن را به `.env` تغییر دهید و اطلاعات خود را وارد کنید:
```bash
cp .env.example .env
```

۳. کانتینرها را با داکر بیلد و اجرا کنید:
```bash
docker-compose up -d --build
```

۴. لاگ‌ها را برای اطمینان از عملکرد بررسی کنید:
```bash
docker-compose logs -f bot
```

۵. داشبورد وب در آدرس `http://localhost:8000` در دسترس خواهد بود.

## 💻 راه‌اندازی بدون Docker (لوکال)

۱. مطمئن شوید که سرور Redis در حال اجرا است (پورت 6379).

۲. پکیج‌های پایتون را نصب کنید:
```bash
pip install -r requirements.txt
```

۳. فایل `.env` را ایجاد و متغیرها را پر کنید.

۴. داشبورد را در یک ترمینال اجرا کنید:
```bash
uvicorn dashboard:app --host 0.0.0.0 --port 8000
```

۵. ربات را در ترمینال دیگر اجرا کنید:
```bash
python main.py
```

## 🛣️ نقشه راه (Roadmap)
- ذخیره شرط‌های بسته شده در دیتابیس با دکمه‌های تعاملی تلگرام
- اضافه کردن Machine Learning برای پیش‌بینی احتمال Limit شدن اکانت
- پشتیبانی مستقیم از API بوکی‌ها جهت Automation ثبت شرط
- اضافه کردن تست‌های اتوماتیک (Pytest)
