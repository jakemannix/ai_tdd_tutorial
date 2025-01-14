# services/auth/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from auth_service.main import app
from auth_service.models import Base

# Use in-memory SQLite for testing (sync version)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        echo=True,
    )
    
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def test_db(test_db_engine) -> Generator[Session, None, None]:
    """Get a test database session."""
    SessionLocal = sessionmaker(
        test_db_engine,
        expire_on_commit=False
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client() -> TestClient:
    """Get a test client."""
    return TestClient(app)

