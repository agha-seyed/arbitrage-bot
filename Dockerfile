FROM python:3.11-slim

# نصب پیش‌نیازهای سیستمی برای Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# کپی فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نصب مرورگر برای Playwright
RUN playwright install chromium
RUN playwright install-deps

# کپی تمام فایل‌های پروژه
COPY . .

# اجرای اسکریپت اصلی
CMD ["python", "main.py"]