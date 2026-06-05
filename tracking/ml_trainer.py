import pandas as pd
import structlog
from sqlalchemy.orm import Session
from tracking.db_session import engine
import asyncio

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
except ImportError:
    pass

log = structlog.get_logger()

class MLTrainer:
    """
    اسکریپت آموزش مدل یادگیری ماشین برای پیش‌بینی Palpable Errors
    و کیفیت واقعی شرط‌ها (CLV مثبت یا منفی).
    """
    
    def fetch_data_from_db(self) -> pd.DataFrame:
        """واکشی تمام رکوردهای دیتابیس برای آموزش"""
        # در اینجا از pandas برای اتصال مستقیم به SQL استفاده می‌کنیم
        query = "SELECT profit_pct, is_steamed, quality, closing_clv, is_palpable_error FROM opportunities WHERE closing_clv IS NOT NULL"
        # چون از async_engine استفاده کردیم، برای pandas باید کانکشن سینک استفاده کنیم.
        # اما در اینجا یک Mock DataFrame می‌سازیم برای نمایش سناریو
        log.info("fetching_data_for_ml")
        
        # Mock Data (در نسخه نهایی pd.read_sql_query(query, sync_engine))
        data = {
            "profit_pct": [1.5, 5.0, 2.0, 10.0, 1.2],
            "is_steamed": [0, 1, 0, 1, 0],
            "quality_encoded": [1, 0, 1, 0, 1], # 1=HIGH, 0=LOW
            "is_palpable_error": [0, 1, 0, 1, 0] # 1=Error (Bad), 0=Good
        }
        return pd.DataFrame(data)
        
    def train_model(self):
        log.info("ml_training_started")
        
        df = self.fetch_data_from_db()
        if df.empty or len(df) < 5:
            log.warning("not_enough_data_for_ml")
            return
            
        # فیچرها (X) و تارگت (y)
        X = df[['profit_pct', 'is_steamed', 'quality_encoded']]
        y = df['is_palpable_error']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        y_pred = clf.predict(X_test)
        
        log.info("ml_training_completed")
        print("Classification Report:")
        print(classification_report(y_test, y_pred))
        
        # ذخیره مدل (joblib.dump(clf, 'palpable_error_predictor.pkl'))
        return clf

if __name__ == "__main__":
    trainer = MLTrainer()
    trainer.train_model()
