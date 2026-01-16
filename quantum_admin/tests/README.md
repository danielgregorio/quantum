# Quantum Admin - Test Suite

Comprehensive test suite for Quantum Admin API and services.

## 📊 Test Structure

```
tests/
├── conftest.py              # Pytest configuration & fixtures
├── unit/                    # Unit tests (isolated components)
│   ├── test_auth.py         # Authentication service tests
│   ├── test_ai_agent.py     # AI agent tests
│   ├── test_docker.py       # Docker service tests (TODO)
│   └── test_schema.py       # Schema inspector tests (TODO)
├── integration/             # Integration tests (API endpoints)
│   └── test_api.py          # API endpoint tests (TODO)
└── e2e/                     # End-to-end tests (user flows)
    └── test_flows.py        # User journey tests (TODO)
```

## 🚀 Running Tests

### Run All Tests
```bash
cd quantum_admin
pytest
```

### Run Specific Test Files
```bash
pytest tests/unit/test_auth.py
pytest tests/unit/test_ai_agent.py
```

### Run Tests by Marker
```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m auth          # Only auth tests
pytest -m ai            # Only AI tests
```

### Run with Coverage
```bash
pytest --cov=backend --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Verbose
```bash
pytest -v -s            # Show print statements
```

## 🎯 Test Coverage Goals

| Component | Current | Target |
|-----------|---------|--------|
| **Auth Service** | ✅ 90%+ | 95% |
| **AI Agent** | ✅ 85%+ | 90% |
| **Docker Service** | ⏳ 0% | 80% |
| **Schema Inspector** | ⏳ 0% | 85% |
| **API Endpoints** | ⏳ 0% | 80% |
| **Overall** | 🎯 50%+ | 80% |

## 📝 Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.integration
@pytest.mark.slow
def test_api_endpoint():
    pass
```

Available markers:
- `unit` - Unit tests
- `integration` - Integration tests
- `e2e` - End-to-end tests
- `slow` - Slow running tests
- `auth` - Authentication tests
- `docker` - Docker-related tests
- `ai` - AI/ML tests
- `db` - Database tests

## 🧪 Writing Tests

### Unit Test Example
```python
def test_user_creation(test_db, user_factory):
    """Test creating a new user"""
    auth_service = AuthService(test_db)
    user_data = user_factory(username="testuser")

    user = auth_service.create_user(user_data)

    assert user.username == "testuser"
    assert user.is_active is True
```

### Integration Test Example
```python
def test_login_endpoint(client):
    """Test POST /auth/login"""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
```

## 🔧 Fixtures Available

### Database Fixtures
- `test_db` - Fresh database session for each test
- `test_db_engine` - Test database engine

### Client Fixtures
- `client` - FastAPI test client
- `authenticated_client` - Test client with auth token

### Factory Fixtures
- `user_factory()` - Create test users
- `container_factory()` - Create test containers

### Mock Fixtures
- `mock_docker_service` - Mock Docker daemon
- `mock_ollama` - Mock AI service

## 📦 Dependencies

Test dependencies (already in requirements-admin.txt):
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- httpx (for async API tests)

## 🐛 Debugging Tests

### Run Single Test
```bash
pytest tests/unit/test_auth.py::TestAuthService::test_create_user -v
```

### Drop into Debugger on Failure
```bash
pytest --pdb
```

### Show Print Statements
```bash
pytest -s
```

## ✅ CI/CD Integration

Tests run automatically on:
- Every commit
- Pull requests
- Before deployment

Minimum requirements:
- All tests must pass
- Coverage must be >= 50%
- No security vulnerabilities

## 📈 Progress Tracker

### Completed ✅
- [x] Test infrastructure (conftest.py)
- [x] Auth service tests (20+ tests)
- [x] AI agent tests (15+ tests)
- [x] Pytest configuration

### In Progress 🏗️
- [ ] Docker service tests
- [ ] Schema inspector tests
- [ ] API integration tests

### Planned 📋
- [ ] E2E user flow tests
- [ ] Performance tests
- [ ] Security tests
- [ ] Load tests

## 🎓 Best Practices

1. **One assertion per test** (when possible)
2. **Use descriptive test names**
3. **AAA pattern**: Arrange, Act, Assert
4. **Isolate tests** - no dependencies between tests
5. **Mock external services** (Docker, Ollama, etc.)
6. **Clean up after tests** (fixtures handle this)
7. **Test both success and failure cases**

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**Target:** 80% coverage by end of Phase 1 🎯
