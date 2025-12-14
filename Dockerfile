# Dockerfile — GOD MODE v8.0 🚀
FROM python:3.11-slim

WORKDIR /app

# نصب فقط چیزایی که نیاز داریم
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نصب پکیج‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# پوشه‌های لاگ و صدا
RUN mkdir -p /app/logs /app/assets

# کپی کد
COPY . .

# چک زنده بودن ربات (برای Render)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python healthcheck.py || exit 1

CMD ["python", "main.py"]