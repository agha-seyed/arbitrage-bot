import json
import logging
import asyncio
from datetime import datetime
from engine.arbitrage_engine import calculate_stakes

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("Backtest")

class BacktestEngine:
    def __init__(self, initial_bankroll=1000):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.trades = []
        
    def load_historical_data(self, filepath):
        """Mock loading historical data. In production, this would fetch from The-Odds-API historical endpoints."""
        logger.info(f"Loading historical data from {filepath}")
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File {filepath} not found. Using mock simulation data.")
            return self._generate_mock_data()
            
    def _generate_mock_data(self):
        """Generate some fake surebets to test the backtester logic"""
        return [
            {"event": "Juventus vs AC Milan", "profit_pct": 2.5, "odds": [2.10, 3.50, 4.00], "bookies": ["snai", "sisal", "eurobet"]},
            {"event": "Inter vs Roma", "profit_pct": 1.2, "odds": [1.80, 4.00, 5.00], "bookies": ["williamhill", "betway", "snai"]},
            {"event": "Napoli vs Lazio", "profit_pct": -0.5, "odds": [2.00, 3.20, 3.50], "bookies": ["sisal", "eurobet", "bet365"]}, # Not an arb
            {"event": "Atalanta vs Fiorentina", "profit_pct": 3.1, "odds": [2.50, 3.50, 3.20], "bookies": ["snai", "eurobet", "betway"]}
        ]

    def run(self, data):
        logger.info(f"Starting backtest with initial bankroll: €{self.initial_bankroll}")
        
        for idx, match in enumerate(data):
            if match["profit_pct"] <= 0:
                logger.info(f"[{idx}] Skipping {match['event']} - No arbitrage (Profit: {match['profit_pct']}%)")
                continue
                
            odds = match["odds"]
            bookies = match["bookies"]
            
            # Calculate stakes based on current bankroll (10% of bankroll per trade)
            current_trade_bankroll = self.bankroll * 0.10
            stakes = calculate_stakes(current_trade_bankroll, odds, match["profit_pct"], bookies)
            
            if stakes:
                total_stake = sum(stakes)
                profit = round(total_stake * (match["profit_pct"] / 100), 2)
                
                # Simulate winning/losing legs. In an arbitrage, one leg wins, others lose.
                # The net change to bankroll is the profit!
                self.bankroll += profit
                
                self.trades.append({
                    "event": match["event"],
                    "total_stake": total_stake,
                    "profit": profit,
                    "roi": match["profit_pct"],
                    "new_bankroll": round(self.bankroll, 2)
                })
                logger.info(f"[{idx}] TRADE EXECUTED: {match['event']} | ROI: {match['profit_pct']}% | Profit: €{profit} | Bankroll: €{round(self.bankroll, 2)}")
                
        self._print_summary()
        
    def _print_summary(self):
        print("\n" + "="*50)
        print("📊 BACKTEST SUMMARY")
        print("="*50)
        print(f"Total Trades Executed: {len(self.trades)}")
        print(f"Initial Bankroll: €{self.initial_bankroll}")
        print(f"Final Bankroll: €{round(self.bankroll, 2)}")
        net_profit = self.bankroll - self.initial_bankroll
        roi = (net_profit / self.initial_bankroll) * 100
        print(f"Net Profit: €{round(net_profit, 2)}")
        print(f"Total ROI: {round(roi, 2)}%")
        print("="*50)

if __name__ == "__main__":
    engine = BacktestEngine(initial_bankroll=1000)
    data = engine.load_historical_data("data/historical_odds.json")
    engine.run(data)
