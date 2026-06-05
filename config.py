from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # API Keys
    ODDS_API_KEY: str = ""
    ODDS_API_FALLBACK_KEY: str = ""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Scan Settings
    SCAN_INTERVAL_SECONDS: int = 30
    BOOKMAKERS_LIST: str = "snai,eurobet,sisal,bet365_it,lottomatica,goldbet,planetwin365,pinnacle,betfair_ex,matchbook,betdaq"
    
    # Profit Thresholds (%)
    MIN_PROFIT_VERY_CLOSE: float = 3.0
    MIN_PROFIT_CLOSE: float = 2.0
    MIN_PROFIT_MEDIUM: float = 1.5
    MIN_PROFIT_FAR: float = 1.0
    
    # Odds Verification
    MAX_ODDS_DEVIATION: float = 0.02
    VERIFY_DELAY_SECONDS: float = 1.0
    
    # Bankroll
    TOTAL_BANKROLL_EUR: float = 100.0
    MAX_SINGLE_BET_PCT: float = 0.20
    MIN_STAKE_EUR: float = 2.0
    
    # Database (Default to SQLite async if not provided)
    DATABASE_URL: str = "sqlite+aiosqlite:///arbitrage.db"
    
    # Dashboard
    DASHBOARD_PORT: int = int(__import__("os").environ.get("PORT", 8080))
    DASHBOARD_HOST: str = "0.0.0.0"

    # Playwright Auto-Betting
    ENABLE_AUTO_BETTING: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
