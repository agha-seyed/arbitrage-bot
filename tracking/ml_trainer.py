import asyncio
import pickle
import os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from database.db_session import get_stats_for_ml
import structlog

log = structlog.get_logger()

MODEL_PATH = "models/arb_predictor.pkl"
ENCODER_PATH = "models/label_encoders.pkl"

def build_features(signal: dict) -> list[float] | None:
    """
    از یک رکورد دیتابیس، ویژگیهای عددی (Feature Vector) بساز.
    خروجی: لیست ۸ عددی یا None اگر داده ناقص بود.
    """
    try:
        from datetime import datetime, timezone
        detected = datetime.fromisoformat(signal['detected_at'])
        # ساعت شبانهروز (بازارهای صبح vs شب متفاوتاند)
        hour_of_day = detected.hour

        profit = float(signal['profit_pct'])
        odd1   = float(signal.get('odd_1', 2.0))
        odd2   = float(signal.get('odd_2', 2.0))
        stake1 = float(signal.get('stake_1', 0))
        stake2 = float(signal.get('stake_2', 0))

        # نسبت بزرگترین به کوچکترین شرط (تعادل دو طرف)
        stake_ratio = max(stake1, stake2) / (min(stake1, stake2) + 0.01)

        # میانگین ضرایب (هرچه بالاتر، ریسک بیشتر)
        avg_odd = (odd1 + odd2) / 2

        # کد کیفیت: HIGH=2, MEDIUM=1, LOW=0
        quality_map = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        quality_score = quality_map.get(signal.get('quality', 'MEDIUM'), 1)

        return [
            profit,
            odd1,
            odd2,
            avg_odd,
            stake_ratio,
            quality_score,
            hour_of_day,
            1 if signal.get('status') == 'void' else 0,   # آیا قبلاً void داشته؟
        ]
    except (KeyError, ValueError, TypeError) as e:
        log.debug("feature_build_failed", error=str(e))
        return None

def label_signal(signal: dict) -> int | None:
    """
    ۱ = موفق (win)
    ۰ = ناموفق (loss یا void)
    None = نادیده بگیر (pending/skipped)
    """
    status = signal.get('status', '')
    if status == 'win':   return 1
    if status in ('loss', 'void'): return 0
    return None

async def train_model():
    """آموزش مدل Random Forest روی دادههای تاریخی"""
    log.info("ml_training_started")

    signals = await get_stats_for_ml()
    log.info("training_data_loaded", count=len(signals))

    if len(signals) < 30:
        log.warning("insufficient_data", count=len(signals), minimum=30)
        print(f"⚠️ داده کافی نیست ({len(signals)} رکورد). حداقل ۳۰ رکورد لازم است.")
        return None

    X, y = [], []
    for signal in signals:
        features = build_features(signal)
        label    = label_signal(signal)
        if features is not None and label is not None:
            X.append(features)
            y.append(label)

    if len(X) < 20:
        log.warning("usable_samples_too_low", count=len(X))
        return None

    X = np.array(X)
    y = np.array(y)

    log.info("training_samples", total=len(X), wins=sum(y), losses=len(y)-sum(y))

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=3,
        class_weight='balanced',   # مهم: دادههای نامتعادل
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # ارزیابی
    y_pred = model.predict(X_test)
    print("\n📊 گزارش ارزیابی مدل:")
    print(classification_report(y_test, y_pred, target_names=['Loss/Void', 'Win']))

    cv_scores = cross_val_score(model, X, y, cv=5, scoring='f1')
    print(f"Cross-validation F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Feature Importance
    feature_names = [
        'profit_pct', 'odd_1', 'odd_2', 'avg_odd',
        'stake_ratio', 'quality_score', 'hour_of_day', 'has_void_history'
    ]
    importance = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1], reverse=True
    )
    print("\n🎯 اهمیت ویژگیها:")
    for fname, imp in importance:
        print(f"  {fname:<20} {imp:.3f}")

    # ذخیره مدل
    os.makedirs("models", exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)

    log.info("model_saved", path=MODEL_PATH, samples=len(X))
    print(f"\n✅ مدل در {MODEL_PATH} ذخیره شد.")
    return model

def predict_signal(opportunity: dict) -> dict:
    """
    احتمال موفقیت یک سیگنال را پیشبینی کن.
    این تابع از pipeline فراخوانی میشود (اختیاری — فقط برای اطلاعات).
    """
    if not os.path.exists(MODEL_PATH):
        return {"probability": None, "prediction": None, "note": "مدل هنوز آموزش ندیده"}

    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)

    # ساخت سیگنال fake برای feature extraction
    legs = opportunity.get('legs', [])
    fake_signal = {
        'profit_pct': opportunity.get('profit_pct', 1.5),
        'odd_1': legs[0].get('odd', 2.0) if legs else 2.0,
        'odd_2': legs[1].get('odd', 2.0) if len(legs) > 1 else 2.0,
        'stake_1': legs[0].get('stake', 50) if legs else 50,
        'stake_2': legs[1].get('stake', 50) if len(legs) > 1 else 50,
        'quality': opportunity.get('quality', {}).get('quality', 'MEDIUM'),
        'detected_at': opportunity.get('detected_at', '2025-01-01T12:00:00'),
        'status': 'win',   # dummy
    }

    features = build_features(fake_signal)
    if features is None:
        return {"probability": None, "prediction": None, "note": "ویژگیها ناقص"}

    prob = model.predict_proba([features])[0][1]   # احتمال win
    prediction = "WIN" if prob >= 0.55 else "LOSS"

    return {
        "probability": round(prob, 3),
        "prediction": prediction,
        "note": f"مدل پیشبینی میکند: {prediction} ({prob*100:.1f}%)"
    }

async def main():
    await train_model()

if __name__ == "__main__":
    asyncio.run(main())
