import asyncio
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import Base, get_db
from app.api.endpoints import router
# Assuming there is a main app entry point, usually 'main.py', but based on file list we might need to construct the app or import it.
# If 'app/main.py' exists we import 'app', otherwise we create a basic FastAPI app for testing using the router.
# Let's check if there is a main.py. If not we'll create a dummy app here or assume standard structure.
# For now, I will assume I can import `app` from `app.main`. If not, I will construct it.
# Looking at the file list, I don't see `main.py` explicitly in "Other open documents".
# However, I should check if I can construct it.
# To be safe, I will try to import `app` from `app.main` inside the fixture or assume I need to build it if it fails?
# No, let's look at `endpoints.py`, it defines a `router`.
# I'll create a minimal FastAPI app in conftest to mount the router if I can't find `main.py`.
# But usually `app.main` is standard. Let's try to import it, if not found, we build one.

from fastapi import FastAPI

# --- Defines ---

# Use the existing DATABASE_URL. In a real CI, this might be overridden.
# We assume the user runs this with a valid Postgres URL.
TEST_DATABASE_URL = settings.DATABASE_URL

# Create a specific engine for testing. 
# NullPool is important for async tests to avoid connection locking issues during rapid test execution 
# if not managed perfectly, though often standard pool is fine.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)

# Session factory bound to the test engine
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# event_loop fixture removal as it is deprecated in pytest-asyncio and causes issues
# We rely on default loop provided by plugin or implicit behavior


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
    
    # Optional: cleanup
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a new database session with a rollback transaction for each test.
    """
    # Start a connection
    connection = await test_engine.connect()
    # Begin a transaction
    transaction = await connection.begin()
    
    # Bind the session to this specific connection
    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    session = session_factory()

    yield session

    # Rollback the transaction after the test
    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Returns a TestClient with authorized headers and overridden DB dependency.
    """
    # Create a wrapper for the app. 
    # Since we don't have main.py in the context, let's create a fresh app and include the router.
    # If the user has a main.py, they should ideally expose `app`.
    # I will create a temporary app for testing to ensure isolation and control.
    test_app = FastAPI()
    test_app.include_router(router) # Mounts the router from endpoints.py directly to root or prefix?
    # endpoints.py router usually has prefixes defined when included in main.
    # Let's check endpoints.py... it uses @router.get("/buildings/...") -> so paths are absolute relative to router.
    # So we can just include it.
    
    # Dependency Override
    async def override_get_db():
        yield session

    test_app.dependency_overrides[get_db] = override_get_db

    headers = {"X-API-Key": settings.API_KEY}
    
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        ac.headers.update(headers)
        yield ac
