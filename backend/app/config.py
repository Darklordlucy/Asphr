from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
    MAPBOX_TOKEN: str = ""
    OPENWEATHER_API_KEY: str = ""
    TOMTOM_API_KEY: str = ""
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure we use asyncpg driver for async SQLAlchemy engine
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure the async engine to be robust and compatible with Supabase/Supavisor connection pooling.
# Supabase transaction pooler (port 6543) doesn't support prepared statements, 
# so we disable the prepared statement cache in asyncpg.
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args={
        "prepared_statement_cache_size": 0,
    }
)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
