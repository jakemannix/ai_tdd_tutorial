# services/auth/tests/conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio
from typing import Generator, AsyncGenerator

from auth_service.main import app, get_db
from auth_service.models import Base

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=True,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def test_db(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Get a test database session."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Get a test client."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

# services/auth/tests/test_auth.py
import pytest
from httpx import AsyncClient
import hashlib
import base64
import os

async def test_registration_flow_success(client: AsyncClient):
    """Test the complete registration flow with valid data."""
    # Step 1: Request registration nonce
    response = await client.post(
        "/auth/register/init",
        json={
            "username": "testuser",
            "email": "test@example.com"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "nonce" in data
    nonce = data["nonce"]
    
    # Step 2: Client-side password handling (simulating frontend)
    password = "this is a secure passphrase that has good entropy"
    client_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        base64.b64decode(nonce),
        100_000,  # iterations
        dklen=32  # length of the derived key
    )
    client_hash_b64 = base64.b64encode(client_hash).decode()
    
    # Step 3: Complete registration
    response = await client.post(
        "/auth/register/complete",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "nonce": nonce,
            "hashed_password": client_hash_b64
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data  # Should return the new user's ID
    assert "username" in data
    assert data["username"] == "testuser"

async def test_registration_duplicate_username(client: AsyncClient):
    """Test that registration fails with duplicate username."""
    # First registration
    init_resp = await client.post(
        "/auth/register/init",
        json={
            "username": "testuser",
            "email": "test1@example.com"
        }
    )
    data = init_resp.json()
    nonce = data["nonce"]
    
    password = "this is a secure passphrase"
    client_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        base64.b64decode(nonce),
        100_000,
        dklen=32
    )
    client_hash_b64 = base64.b64encode(client_hash).decode()
    
    await client.post(
        "/auth/register/complete",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "nonce": nonce,
            "hashed_password": client_hash_b64
        }
    )
    
    # Try to register same username
    response = await client.post(
        "/auth/register/init",
        json={
            "username": "testuser",
            "email": "test2@example.com"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "username already exists" in data["detail"].lower()

async def test_registration_invalid_nonce(client: AsyncClient):
    """Test that registration fails with invalid nonce."""
    # Get valid nonce first
    init_resp = await client.post(
        "/auth/register/init",
        json={
            "username": "testuser",
            "email": "test@example.com"
        }
    )
    assert init_resp.status_code == 200
    
    # Try to complete with invalid nonce
    invalid_nonce = base64.b64encode(os.urandom(32)).decode()
    response = await client.post(
        "/auth/register/complete",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "nonce": invalid_nonce,
            "hashed_password": "somehash"
        }
    )
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "invalid nonce" in data["detail"].lower()

