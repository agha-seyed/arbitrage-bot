# healthcheck.py
import os
from datetime import datetime
print(f"ربات زنده است — {datetime.utcnow().isoformat()} — حالت تست: {'فعال' if os.getenv('DRY_RUN', 'true').lower() == 'true' else 'غیرفعال'}")
exit(0)