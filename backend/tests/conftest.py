"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_async_db
from app.config import get_settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

settings = get_settings()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(test_session):
    """Create test client with database override."""
    
    async def get_test_db():
        yield test_session
    
    app.dependency_overrides[get_async_db] = get_test_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return [
        {
            "id": "1",
            "amount": 100.0,
            "timestamp": "2024-01-01T10:00:00Z",
            "account_id": "ACC001",
            "description": "Test transaction 1"
        },
        {
            "id": "2",
            "amount": 200.0,
            "timestamp": "2024-01-01T11:00:00Z",
            "account_id": "ACC001",
            "description": "Test transaction 2"
        },
        {
            "id": "3",
            "amount": 1000.0,
            "timestamp": "2024-01-01T12:00:00Z",
            "account_id": "ACC001",
            "description": "Large transaction"
        }
    ]


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for file upload testing."""
    return b"""id,amount,timestamp,account_id,description
1,100.0,2024-01-01T10:00:00Z,ACC001,Test transaction 1
2,200.0,2024-01-01T11:00:00Z,ACC001,Test transaction 2
3,1000.0,2024-01-01T12:00:00Z,ACC001,Large transaction"""


@pytest.fixture
def sample_json_content():
    """Sample JSON content for file upload testing."""
    return b"""[
    {
        "id": "1",
        "amount": 100.0,
        "timestamp": "2024-01-01T10:00:00Z",
        "account_id": "ACC001",
        "description": "Test transaction 1"
    },
    {
        "id": "2", 
        "amount": 200.0,
        "timestamp": "2024-01-01T11:00:00Z",
        "account_id": "ACC001",
        "description": "Test transaction 2"
    }
]""" 