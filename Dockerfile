# استفاده از ایمیج رسمی Playwright که تمام پیش‌نیازها و مرورگرها از قبل روی آن نصب است
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# کپی فایل نیازمندی‌ها و نصب آن‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی تمام فایل‌های پروژه
COPY . .

# اجرای اسکریپت اصلی
CMD ["python", "main.py"]