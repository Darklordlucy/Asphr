import datetime
import logging
from sqlalchemy import delete
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import AsyncSessionLocal
from app.models.db_models import SegmentHazard
from app.services.weather_service import refresh_weather_grid
from app.algorithms.graph_builder import GraphManager
from app.services.websocket_manager import websocket_manager

logger = logging.getLogger("app.scheduler")

# Create the AsyncIOScheduler instance
scheduler = AsyncIOScheduler()

async def refresh_weather_grid_job():
    """Scheduled job to refresh weather data every 10 minutes."""
    logger.info("Executing scheduled weather grid refresh...")
    try:
        await refresh_weather_grid()
        # Broadcast weather update event to connected WebSocket clients
        await websocket_manager.broadcast({
            "type": "weather_updated",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error during scheduled weather refresh: {e}")

async def enrich_graph_weights_job():
    """Scheduled job to recompute graph edge weights every 5 minutes."""
    logger.info("Executing scheduled graph weight enrichment...")
    try:
        async with AsyncSessionLocal() as session:
            manager = GraphManager.get_instance()
            # Ensure the graph is loaded before enriching
            manager.get_graph()
            await manager.enrich_graph_weights(session)
            manager.last_updated = datetime.datetime.now()
            
        logger.info("Successfully completed scheduled graph weight enrichment.")
        # Broadcast graph refreshed event to connected WebSocket clients
        await websocket_manager.broadcast({
            "type": "graph_refreshed",
            "timestamp": manager.last_updated.isoformat(),
            "status": "success"
        })
    except Exception as e:
        logger.error(f"Error during scheduled graph weights enrichment: {e}")

async def expire_old_hazards_job():
    """Scheduled job to expire and delete old segment hazard records."""
    logger.info("Executing scheduled hazard expiration...")
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.datetime.utcnow()
            # Default hazard lifetime of 2 hours if expires_at is null
            default_cutoff = now - datetime.timedelta(hours=2)
            
            stmt = delete(SegmentHazard).where(
                (SegmentHazard.expires_at < now) |
                ((SegmentHazard.expires_at == None) & (SegmentHazard.recorded_at < default_cutoff))
            )
            result = await db.execute(stmt)
            await db.commit()
            
            expired_count = result.rowcount or 0
            if expired_count > 0:
                logger.info(f"Expired and deleted {expired_count} old segment hazard records.")
                # Broadcast hazard expiration event to connected WebSocket clients
                await websocket_manager.broadcast({
                    "type": "hazards_expired",
                    "timestamp": now.isoformat(),
                    "count": expired_count
                })
            else:
                logger.debug("No expired hazards found.")
    except Exception as e:
        logger.error(f"Error during scheduled hazard expiration: {e}")

def setup_scheduler():
    """Add scheduled jobs to the scheduler."""
    # Run weather grid refresh every 10 minutes
    scheduler.add_job(
        refresh_weather_grid_job,
        "interval",
        minutes=10,
        id="weather_refresh",
        replace_existing=True
    )
    
    # Run graph weight enrichment every 5 minutes
    scheduler.add_job(
        enrich_graph_weights_job,
        "interval",
        minutes=5,
        id="graph_enrichment",
        replace_existing=True
    )
    
    # Run hazard expiration every 5 minutes
    scheduler.add_job(
        expire_old_hazards_job,
        "interval",
        minutes=5,
        id="hazard_expiration",
        replace_existing=True
    )
    
    logger.info("Scheduler setup complete: registered weather_refresh (10m), graph_enrichment (5m), hazard_expiration (5m).")
