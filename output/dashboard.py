from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import redis.asyncio as aioredis
from protection.account_health import AccountHealthMonitor
from tracking.clv_tracker import CLVTracker
from config import settings
from config import settings
import structlog

log = structlog.get_logger()

class Dashboard:
    def __init__(self, health_monitor: AccountHealthMonitor, clv_tracker: CLVTracker, redis_client: aioredis.Redis):
        self.health_monitor = health_monitor
        self.clv_tracker = clv_tracker
        self.redis = redis_client
        self.app = FastAPI()
        
        # HTML template is expected to be in templates/index.html
        self.templates = Jinja2Templates(directory="templates")
        
        @self.app.get("/", response_class=HTMLResponse)
        async def root(request: Request):
            return self.templates.TemplateResponse("index.html", {"request": request})
            
        @self.app.get("/api/stats")
        async def get_stats():
            """آمار کلی برای داشبورد"""
            avg_clv = await self.clv_tracker.get_average_clv(days=30)
            all_scores = await self.health_monitor.get_all_scores()
            
            healthy_count = sum(1 for s in all_scores.values() if s['score'] >= 80)
            warning_count = sum(1 for s in all_scores.values() if 50 <= s['score'] < 80)
            critical_count = sum(1 for s in all_scores.values() if s['score'] < 50)
            
            return {
                "clv_30d": round(avg_clv, 2),
                "accounts": {
                    "healthy": healthy_count,
                    "warning": warning_count,
                    "critical": critical_count
                }
            }
            
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            try:
                while True:
                    scores = await self.health_monitor.get_all_scores()
                    await websocket.send_json({"health_scores": scores})
                    await asyncio.sleep(60)
            except Exception as e:
                log.info("websocket_disconnected", error=str(e))
                
    async def start_server(self):
        config = uvicorn.Config(
            app=self.app, 
            host=settings.DASHBOARD_HOST, 
            port=settings.DASHBOARD_PORT, 
            log_level="warning"
        )
        server = uvicorn.Server(config)
        await server.serve()
