import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("ML-Predictor")

class ArbitragePredictor:
    def __init__(self, model_path="models/arb_model.pkl"):
        self.model_path = model_path
        self.model = None
        
    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info("Model loaded successfully.")
            return True
        return False
        
    def train(self, data_file="data/historical_trades.csv"):
        """Train a Machine Learning model to predict if an arbitrage opportunity will be profitable long-term or result in a void/limited bet."""
        logger.info(f"Loading historical data from {data_file}...")
        
        # Mock data generation if file doesn't exist
        if not os.path.exists(data_file):
            logger.warning(f"File {data_file} not found. Generating mock training data...")
            self._generate_mock_csv(data_file)
            
        df = pd.read_csv(data_file)
        
        # Features: Profit Percentage, Implied Probability, Number of Bookies, Market Type (H2H=1, Totals=2)
        X = df[['profit_pct', 'implied_prob', 'num_bookies', 'market_type']]
        # Target: 1 if successful without limit/void, 0 if problematic
        y = df['is_successful']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        logger.info("Training Random Forest Classifier (Phase 3 XGBoost preparation)...")
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        predictions = self.model.predict(X_test)
        acc = accuracy_score(y_test, predictions)
        
        logger.info(f"Model Training Complete! Accuracy: {acc * 100:.2f}%")
        logger.info("\n" + classification_report(y_test, predictions))
        
        # Ensure models directory exists
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")
        
    def predict(self, profit_pct, implied_prob, num_bookies, market_type):
        if not self.model:
            if not self.load_model():
                logger.error("No model found. Please train the model first.")
                return None
                
        features = np.array([[profit_pct, implied_prob, num_bookies, market_type]])
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0][1]
        
        return {
            "is_safe": bool(prediction),
            "confidence": round(probability * 100, 2)
        }
        
    def _generate_mock_csv(self, file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Generate 1000 mock rows
        np.random.seed(42)
        profits = np.random.uniform(0.1, 10.0, 1000)
        implied_probs = np.random.uniform(0.7, 0.99, 1000)
        num_bookies = np.random.choice([2, 3], 1000)
        market_types = np.random.choice([1, 2], 1000)
        
        # Logic for mock success: High profit (>7%) is risky (palpable error), high implied prob is safer
        success = ((profits < 7.0) & (implied_probs > 0.8)).astype(int)
        
        # Add some noise
        noise = np.random.choice([0, 1], 1000, p=[0.9, 0.1])
        success = np.abs(success - noise)
        
        df = pd.DataFrame({
            'profit_pct': profits,
            'implied_prob': implied_probs,
            'num_bookies': num_bookies,
            'market_type': market_types,
            'is_successful': success
        })
        df.to_csv(file_path, index=False)

if __name__ == "__main__":
    predictor = ArbitragePredictor()
    predictor.train()
    
    # Test a prediction
    logger.info("Testing Prediction for 2.5% Profit, 0.95 Implied Prob, 2 Bookies, H2H:")
    res = predictor.predict(profit_pct=2.5, implied_prob=0.95, num_bookies=2, market_type=1)
    logger.info(f"Prediction Result: {res}")
    
    logger.info("Testing Prediction for 15.0% Profit (Palpable Error), 0.85 Implied Prob, 2 Bookies, H2H:")
    res = predictor.predict(profit_pct=15.0, implied_prob=0.85, num_bookies=2, market_type=1)
    logger.info(f"Prediction Result: {res}")
