from fastapi.testclient import TestClient
import hashlib
import base64
import os

def test_registration_flow_success(client: TestClient):
    """Test the complete registration flow with valid data."""
    # Step 1: Request registration nonce
    response = client.post(
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
    response = client.post(
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

def test_registration_duplicate_username(client: TestClient):
    """Test that registration fails with duplicate username."""
    # First registration
    init_resp = client.post(
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
    
    client.post(
        "/auth/register/complete",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "nonce": nonce,
            "hashed_password": client_hash_b64
        }
    )
    
    # Try to register same username
    response = client.post(
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

def test_registration_invalid_nonce(client: TestClient):
    """Test that registration fails with invalid nonce."""
    # Get valid nonce first
    init_resp = client.post(
        "/auth/register/init",
        json={
            "username": "testuser",
            "email": "test@example.com"
        }
    )
    assert init_resp.status_code == 200
    
    # Try to complete with invalid nonce
    invalid_nonce = base64.b64encode(os.urandom(32)).decode()
    response = client.post(
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
