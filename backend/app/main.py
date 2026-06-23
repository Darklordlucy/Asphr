from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, geocode, iot, routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("Initializing Asphr Backend Service...")
    yield
    # Shutdown tasks
    print("Shutting down Asphr Backend Service...")

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
