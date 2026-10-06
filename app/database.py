from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


database_url = settings.sqlalchemy_database_url
connect_args = {}

if database_url.startswith("postgresql+asyncpg://"):
    connect_args["ssl"] = "require"

engine = create_async_engine(
    database_url,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
