import csv
import os
from datetime import datetime
import structlog

log = structlog.get_logger()

class MLCollector:
    """
    ذخیره داده‌های آموزش ماشین
    """
    def __init__(self, filename="ml_data.csv"):
        self.filename = filename
        self._init_csv()
        
    def _init_csv(self):
        if not os.path.exists(self.filename):
            with open(self.filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "timestamp", "event_id", "sport", "profit_pct", 
                    "market_type", "bookies", "status", "reason"
                ])
                
    def record_approved(self, opportunity: dict):
        self._write(opportunity, "APPROVED", "")
        
    def record_rejected(self, opportunity: dict, reason: str):
        self._write(opportunity, "REJECTED", reason)
        
    def _write(self, opp: dict, status: str, reason: str):
        try:
            bookies = "|".join([leg['bookmaker'] for leg in opp.get('legs', [])])
            with open(self.filename, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([
                    datetime.now().isoformat(),
                    opp.get('event_id', ''),
                    opp.get('sport_key', ''),
                    opp.get('profit_pct', 0),
                    opp.get('market_type', ''),
                    bookies,
                    status,
                    reason
                ])
        except Exception as e:
            log.error("ml_collection_error", error=str(e))
