from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import redis.asyncio as redis
import json
import os

app = FastAPI(title="Arbitrage Beast - Dashboard")
templates = Jinja2Templates(directory="templates")

# Use redis from docker if REDIS_HOST isn't set, otherwise default to localhost
redis_host = os.getenv("REDIS_HOST", "redis" if os.getenv("IS_DOCKER") else "localhost")

r = redis.Redis(
    host=redis_host,
    port=6379,
    db=0,
    decode_responses=True
)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Fetch latest 50 signals
    raw_signals = await r.lrange("recent_signals", 0, 49)
    signals = [json.loads(s) for s in raw_signals]
    
    # Calculate some basic stats
    total_found = len(signals)
    avg_profit = round(sum(float(s.get("profit_pct", 0)) for s in signals) / total_found, 2) if total_found > 0 else 0
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "signals": signals,
        "total_found": total_found,
        "avg_profit": avg_profit
    })
