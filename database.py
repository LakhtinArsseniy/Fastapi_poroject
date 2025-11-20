from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:1987@localhost:5432/postgres"

engine = create_async_engine(
    DATABASE_URL,
    echo=True, 
)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
