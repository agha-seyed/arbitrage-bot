"""
این اسکریپت به عنوان یک Worker در پس‌زمینه (مثلاً روزی یک بار توسط Cron) اجرا می‌شود.
وظیفه آن چک کردن وضعیت بازی‌های تمام شده و دریافت ضریب بسته شدن مارکت (Closing Odds) 
از سایت‌های مرجع (مثل Pinnacle) است تا CLV واقعی را محاسبه و آپدیت کند.
"""
import asyncio
import redis.asyncio as redis
from loguru import logger
from engine.clv_tracker import CLVTracker

async def main():
    logger.info("شروع محاسبه‌گر آفلاین CLV...")
    
    r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
    tracker = CLVTracker(r)
    
    # پیدا کردن تمام شرط‌های ثبت شده
    keys = await r.keys("bet:*")
    
    if not keys:
        logger.info("هیچ شرط ثبت‌شده‌ای برای محاسبه CLV یافت نشد.")
        return
        
    for key in keys:
        bet_data = await r.hgetall(key)
        if 'clv' in bet_data:
            continue # قبلا محاسبه شده
            
        event_id = bet_data.get('event_id')
        # TODO: در آینده از طریق API (مثلاً Pinnacle API یا The-Odds-API Archive) 
        # باید closing_odd این رویداد گرفته شود.
        # در اینجا یک شبیه‌سازی انجام می‌دهیم:
        mock_closing_odd = float(bet_data['odd_taken']) * 0.95 # فرض می‌کنیم ضریب 5% افت کرده
        
        # محاسبه
        bet_id = key.split(":")[1]
        clv = await tracker.calculate_clv(bet_id, mock_closing_odd)
        
        if clv is not None:
            logger.info(f"رویداد {event_id} - محاسبه CLV: {clv:.2f}%")
            
    logger.info("پایان اسکن CLV.")
    
if __name__ == "__main__":
    asyncio.run(main())
