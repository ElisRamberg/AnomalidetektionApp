"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
import tempfile
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pandas as pd

from app.main import app
from app.database import get_async_db, Base
from app.models.upload import FileUpload
from app.models.transaction import Transaction
from app.models.analysis import AnalysisRun
from app.models.strategy import Strategy
from app.config import get_settings


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database dependency override."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_async_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# Sample data fixtures
@pytest.fixture
def sample_csv_content() -> bytes:
    """Sample CSV content for testing."""
    return b"""amount,timestamp,account_id,external_transaction_id
100.50,2023-01-01T10:00:00Z,ACC001,TXN001
-25.00,2023-01-01T11:00:00Z,ACC001,TXN002
200.00,2023-01-01T12:00:00Z,ACC002,TXN003
-50.75,2023-01-01T13:00:00Z,ACC002,TXN004
1000.00,2023-01-01T14:00:00Z,ACC003,TXN005"""


@pytest.fixture
def sample_json_content() -> bytes:
    """Sample JSON content for testing."""
    return b"""[
    {
        "amount": 100.50,
        "timestamp": "2023-01-01T10:00:00Z",
        "account_id": "ACC001",
        "external_transaction_id": "TXN001"
    },
    {
        "amount": -25.00,
        "timestamp": "2023-01-01T11:00:00Z", 
        "account_id": "ACC001",
        "external_transaction_id": "TXN002"
    },
    {
        "amount": 200.00,
        "timestamp": "2023-01-01T12:00:00Z",
        "account_id": "ACC002", 
        "external_transaction_id": "TXN003"
    }
]"""


@pytest.fixture
def sample_excel_content() -> bytes:
    """Sample Excel content for testing."""
    # Create a simple Excel file in memory
    import io
    from openpyxl import Workbook
    
    wb = Workbook()
    ws = wb.active
    ws.append(["amount", "timestamp", "account_id", "external_transaction_id"])
    ws.append([100.50, "2023-01-01T10:00:00Z", "ACC001", "TXN001"])
    ws.append([-25.00, "2023-01-01T11:00:00Z", "ACC001", "TXN002"])
    ws.append([200.00, "2023-01-01T12:00:00Z", "ACC002", "TXN003"])
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


@pytest_asyncio.fixture
async def sample_upload(db_session: AsyncSession) -> FileUpload:
    """Create a sample upload record."""
    upload = FileUpload(
        id=uuid.uuid4(),
        filename="test_file.csv",
        original_filename="test.csv",
        file_size=1024,
        file_type="csv",
        mime_type="text/csv",
        status="uploaded",
        metadata={"test": True}
    )
    
    db_session.add(upload)
    await db_session.commit()
    await db_session.refresh(upload)
    return upload


@pytest_asyncio.fixture
async def sample_uploads(db_session: AsyncSession) -> list[FileUpload]:
    """Create multiple sample upload records."""
    uploads = []
    statuses = ["uploaded", "processing", "processed", "failed"]
    
    for i in range(10):
        upload = FileUpload(
            id=uuid.uuid4(),
            filename=f"test_file_{i}.csv",
            original_filename=f"test_{i}.csv",
            file_size=1024 * (i + 1),
            file_type="csv",
            mime_type="text/csv",
            status=statuses[i % len(statuses)],
            metadata={"batch": "test", "index": i}
        )
        uploads.append(upload)
        db_session.add(upload)
    
    await db_session.commit()
    for upload in uploads:
        await db_session.refresh(upload)
    
    return uploads


@pytest_asyncio.fixture
async def sample_transactions(db_session: AsyncSession, sample_upload: FileUpload) -> list[Transaction]:
    """Create sample transaction records."""
    transactions = []
    base_time = datetime(2023, 1, 1, 10, 0, 0)
    
    for i in range(20):
        transaction = Transaction(
            id=uuid.uuid4(),
            upload_id=sample_upload.id,
            amount=100.0 + (i * 10),
            timestamp=base_time.replace(hour=10 + (i % 12)),
            account_id=f"ACC{(i % 3) + 1:03d}",
            external_transaction_id=f"TXN{i+1:03d}",
            raw_data={"original_amount": 100.0 + (i * 10)},
            processed_data={
                "year": 2023,
                "month": 1,
                "day": 1,
                "hour": 10 + (i % 12),
                "day_of_week": 6,  # Sunday
                "is_weekend": True,
                "is_business_hours": i % 2 == 0,
                "amount_abs": 100.0 + (i * 10),
                "is_debit": False,
                "is_credit": True,
                "amount_category": "medium",
                "transaction_sequence": i + 1
            }
        )
        transactions.append(transaction)
        db_session.add(transaction)
    
    await db_session.commit()
    for transaction in transactions:
        await db_session.refresh(transaction)
    
    return transactions


@pytest_asyncio.fixture
async def sample_strategy(db_session: AsyncSession) -> Strategy:
    """Create a sample strategy record."""
    strategy = Strategy(
        id=uuid.uuid4(),
        name="Test Strategy",
        description="A test strategy for anomaly detection",
        configuration={
            "algorithms": [
                {
                    "type": "statistical",
                    "name": "zscore",
                    "enabled": True,
                    "config": {
                        "threshold": 3.0,
                        "window_size": 30
                    }
                },
                {
                    "type": "rule_based",
                    "name": "weekend_threshold",
                    "enabled": True,
                    "config": {
                        "weekend_multiplier": 0.3,
                        "weekday_multiplier": 1.0
                    }
                }
            ],
            "global_settings": {
                "aggregation_method": "max",
                "confidence_threshold": 0.7
            }
        },
        is_active=True,
        created_by="test_user"
    )
    
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def sample_analysis_run(db_session: AsyncSession, sample_upload: FileUpload, 
                             sample_strategy: Strategy) -> AnalysisRun:
    """Create a sample analysis run record."""
    analysis_run = AnalysisRun(
        id=uuid.uuid4(),
        upload_id=sample_upload.id,
        strategy_id=sample_strategy.id,
        status="pending",
        metadata={"test": True}
    )
    
    db_session.add(analysis_run)
    await db_session.commit()
    await db_session.refresh(analysis_run)
    return analysis_run


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample pandas DataFrame for testing."""
    data = {
        'id': [str(uuid.uuid4()) for _ in range(100)],
        'amount': [100.0 + i * 10 for i in range(100)],
        'timestamp': pd.date_range('2023-01-01', periods=100, freq='H'),
        'account_id': [f'ACC{(i % 5) + 1:03d}' for i in range(100)],
        'external_transaction_id': [f'TXN{i+1:03d}' for i in range(100)],
        'year': [2023] * 100,
        'month': [1] * 100,
        'day': [1 + (i // 24) for i in range(100)],
        'hour': [i % 24 for i in range(100)],
        'day_of_week': [(i // 24) % 7 for i in range(100)],
        'is_weekend': [((i // 24) % 7) >= 5 for i in range(100)],
        'is_business_hours': [(i % 24) >= 9 and (i % 24) <= 17 for i in range(100)],
        'amount_abs': [abs(100.0 + i * 10) for i in range(100)],
        'is_debit': [False] * 100,
        'is_credit': [True] * 100,
        'amount_category': ['medium'] * 100,
        'transaction_sequence': list(range(1, 101))
    }
    return pd.DataFrame(data)


# Mock fixtures
@pytest.fixture
def mock_file_processor():
    """Mock file processor service."""
    mock = MagicMock()
    mock.validate_file.return_value = {"valid": True, "message": "File is valid"}
    mock.parse_file.return_value = [
        {
            "amount": 100.0,
            "timestamp": "2023-01-01T10:00:00Z",
            "account_id": "ACC001",
            "external_transaction_id": "TXN001"
        }
    ]
    return mock


@pytest.fixture
def mock_data_transformer():
    """Mock data transformer service."""
    mock = MagicMock()
    mock.transform_transactions.return_value = pd.DataFrame({
        'id': [str(uuid.uuid4())],
        'amount': [100.0],
        'timestamp': [datetime.now()],
        'account_id': ['ACC001'],
        'upload_id': [str(uuid.uuid4())],
        'raw_data': [{}]
    })
    mock.get_transformation_stats.return_value = {
        'original_count': 1,
        'final_count': 1,
        'dropped_count': 0
    }
    return mock


@pytest.fixture
def mock_analysis_engine():
    """Mock analysis engine service."""
    mock = MagicMock()
    mock.run_analysis = AsyncMock(return_value={
        'anomaly_count': 5,
        'total_transactions': 100,
        'anomaly_rate': 0.05
    })
    return mock


@pytest.fixture
def mock_strategy_manager():
    """Mock strategy manager service."""
    mock = MagicMock()
    mock.validate_strategy_configuration.return_value = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    return mock


@pytest.fixture
def mock_algorithm_registry():
    """Mock algorithm registry."""
    mock = MagicMock()
    mock.list_algorithms.return_value = {
        'statistical': ['zscore', 'correlation', 'timeseries'],
        'rule_based': ['weekend_threshold'],
        'ml_based': ['isolation_forest']
    }
    mock.get_algorithm.return_value = MagicMock()
    return mock


# Configuration fixtures
@pytest.fixture
def test_settings():
    """Test application settings."""
    settings = get_settings()
    settings.database_url = TEST_DATABASE_URL
    settings.testing = True
    settings.upload_dir = "/tmp/test_uploads"
    settings.max_file_size = 100 * 1024 * 1024  # 100MB
    settings.file_retention_days = 30
    settings.analysis_retention_days = 90
    return settings


@pytest.fixture(autouse=True)
def setup_test_environment(test_settings):
    """Setup test environment automatically for all tests."""
    # Create test upload directory
    os.makedirs(test_settings.upload_dir, exist_ok=True)
    
    yield
    
    # Cleanup test upload directory
    import shutil
    if os.path.exists(test_settings.upload_dir):
        shutil.rmtree(test_settings.upload_dir)


# Utility fixtures
@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield tmp.name
    
    # Cleanup
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


# Async test helpers
class AsyncContextManager:
    """Helper for testing async context managers."""
    
    def __init__(self, coro):
        self.coro = coro
        
    async def __aenter__(self):
        return await self.coro
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_context_manager():
    """Helper for creating async context managers in tests."""
    return AsyncContextManager 