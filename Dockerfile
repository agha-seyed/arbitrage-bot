FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# کپی فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نصب مرورگر برای Playwright به همراه تمامی پیش‌نیازهای لینوکسی آن
RUN playwright install --with-deps chromium

# کپی تمام فایل‌های پروژه
COPY . .

# اجرای اسکریپت اصلی
CMD ["python", "main.py"]