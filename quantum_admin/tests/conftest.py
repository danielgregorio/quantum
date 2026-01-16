"""
Pytest Configuration and Fixtures
Shared test configuration for all Quantum Admin tests
"""

import pytest
import os
import sys
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import Base
from main import app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create test database engine
    Uses in-memory SQLite for speed
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_db_engine) -> Generator[Session, None, None]:
    """
    Create fresh database session for each test
    Automatically rolls back after each test
    """
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine
    )

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture(scope="module")
def client():
    """
    FastAPI test client
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def authenticated_client(client, test_db):
    """
    Authenticated test client with admin user
    """
    from auth_service import AuthService, UserCreate, UserRole

    # Create test admin user
    auth_service = AuthService(test_db)

    user_data = UserCreate(
        username="testadmin",
        email="testadmin@example.com",
        password="TestPass123!",
        full_name="Test Admin"
    )

    user = auth_service.create_user(user_data)

    # Assign admin role
    admin_role = test_db.query(UserRole).filter(UserRole.name == "admin").first()
    if admin_role:
        user.roles.append(admin_role)
        test_db.commit()

    # Login and get token
    response = client.post("/auth/login", json={
        "username": "testadmin",
        "password": "TestPass123!"
    })

    token = response.json()["access_token"]

    # Return client with auth headers
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client

    # Cleanup
    client.headers.pop("Authorization", None)


# ============================================================================
# Mock Services
# ============================================================================

@pytest.fixture
def mock_docker_service(mocker):
    """
    Mock Docker service for testing without Docker daemon
    """
    mock = mocker.patch('docker_service.DockerService')
    mock.return_value.list_containers.return_value = []
    mock.return_value.create_container.return_value = {"id": "test123"}
    mock.return_value.start_container.return_value = True
    mock.return_value.stop_container.return_value = True
    return mock


@pytest.fixture
def mock_ollama(mocker):
    """
    Mock Ollama service for AI testing
    """
    mock = mocker.patch('ai_agent.SLMProvider')
    mock.return_value.generate.return_value = "Mocked AI response"
    return mock


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def user_factory():
    """
    Factory for creating test users
    """
    def create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123!",
        **kwargs
    ):
        from auth_service import UserCreate
        return UserCreate(
            username=username,
            email=email,
            password=password,
            full_name=kwargs.get('full_name', 'Test User')
        )

    return create_user


@pytest.fixture
def container_factory():
    """
    Factory for creating test container configs
    """
    def create_container(
        name="test-container",
        image="nginx:latest",
        **kwargs
    ):
        return {
            "name": name,
            "image": image,
            "ports": kwargs.get('ports', {"80": "8080"}),
            "env": kwargs.get('env', {}),
            "volumes": kwargs.get('volumes', {})
        }

    return create_container


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """
    Setup test environment variables
    """
    os.environ["TESTING"] = "true"
    os.environ["DEBUG"] = "false"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

    yield

    # Cleanup
    os.environ.pop("TESTING", None)
    os.environ.pop("DEBUG", None)
