from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "password")
    name = os.getenv("DB_NAME", "news_app")
    _database_url = f"mysql+aiomysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"

DATABASE_URL: str = _database_url

SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))

async_engine = create_async_engine(
    DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
