import sys
import os
from pathlib import Path

# Add backend directory to sys.path to resolve 'app' module imports
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings, AsyncSessionLocal
from app.routers import health, geocode, iot, routes, websocket, custom_db
from app.algorithms.graph_builder import GraphManager
from app.models.hazard_predictor import HazardPredictor
from app.models.traffic_forecaster import TrafficForecaster
from app.services.scheduler import scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("Initializing Asphr Backend Service...")
    
    # Run the initial graph load, database synchronization, and weight enrichment asynchronously
    async def load_and_sync_network():
        try:
            print("Beginning background road network initialization...")
            manager = GraphManager.get_instance()
            
            # Load or download the graph (in an executor to avoid blocking the main event loop)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, manager.get_graph)
            
            # Load ML hazard prediction model (before enrichment so it's available)
            project_root = Path(__file__).resolve().parent.parent.parent
            predictor = HazardPredictor.get_instance()
            predictor.load_model(
                model_path=str(project_root / "ml-training" / "models" / "hazard_model.pkl"),
                columns_path=str(project_root / "ml-training" / "models" / "feature_columns.json"),
            )
            
            # Load ML traffic forecasting model
            forecaster = TrafficForecaster.get_instance()
            forecaster.load_model(
                model_path=str(project_root / "ml-training" / "models" / "traffic_forecaster.pt")
            )
            
            # Sync graph to database and enrich
            async with AsyncSessionLocal() as session:
                await manager.sync_graph_to_db(session)
                await manager.enrich_graph_weights(session)
            
            print("Background road network initialization successfully completed.")
            
            # Setup and start APScheduler
            setup_scheduler()
            scheduler.start()
            print("Background scheduler successfully started.")
        except Exception as e:
            print(f"Error during background road network initialization: {e}")
            
    asyncio.create_task(load_and_sync_network())
    
    yield
    
    # Shutdown tasks
    print("Shutting down Asphr Backend Service...")
    try:
        scheduler.shutdown(wait=False)
        print("Background scheduler shut down successfully.")
    except Exception as e:
        print(f"Error during scheduler shutdown: {e}")

app = FastAPI(
    title="Asphr API",
    description="Strategic dynamic routing engine with IoT data integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(geocode.router)
app.include_router(iot.router)
app.include_router(routes.router)
app.include_router(websocket.router)
app.include_router(custom_db.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

