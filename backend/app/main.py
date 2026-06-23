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
from app.routers import health, geocode, iot, routes
from app.algorithms.graph_builder import GraphManager, refresh_graph_periodically


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("Initializing Asphr Backend Service...")
    
    # Start the periodic weight refreshment task in the background
    refresh_task = asyncio.create_task(refresh_graph_periodically())
    
    # Run the initial graph load, database synchronization, and weight enrichment asynchronously
    async def load_and_sync_network():
        try:
            print("Beginning background road network initialization...")
            manager = GraphManager.get_instance()
            
            # Load or download the graph (in an executor to avoid blocking the main event loop)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, manager.get_graph)
            
            # Sync graph to database and enrich
            async with AsyncSessionLocal() as session:
                await manager.sync_graph_to_db(session)
                await manager.enrich_graph_weights(session)
            
            print("Background road network initialization successfully completed.")
        except Exception as e:
            print(f"Error during background road network initialization: {e}")
            
    asyncio.create_task(load_and_sync_network())
    
    yield
    
    # Shutdown tasks
    print("Shutting down Asphr Backend Service...")
    refresh_task.cancel()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
