import asyncio
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.api.endpoints import router
from fastapi import FastAPI

TEST_DATABASE_URL = settings.DATABASE_URL
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    """
    Creates tables at the beginning of the test session.
    Drops them at the end (optional, or leave them).
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    


@pytest.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a new database session with a rollback transaction for each test.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Returns a TestClient with authorized headers and overridden DB dependency.
    """
    test_app = FastAPI()
    test_app.include_router(router)
    
    # Dependency Override
    async def override_get_db():
        yield session

    test_app.dependency_overrides[get_db] = override_get_db

    headers = {"X-API-Key": settings.API_KEY}
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        ac.headers.update(headers)
        yield ac
