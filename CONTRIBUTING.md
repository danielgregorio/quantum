# Contributing to Quantum Admin

Thank you for your interest in contributing to Quantum Admin! This document provides guidelines and instructions for contributing.

## 🚀 Quick Start

### 1. Fork & Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/quantum.git
cd quantum
```

### 2. Setup Development Environment
```bash
cd quantum_admin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-admin.txt

# Install development tools
pip install black ruff mypy bandit safety pre-commit
```

### 3. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 📋 Development Workflow

### 1. Write Code
- Follow PEP 8 style guide
- Add docstrings to functions/classes
- Keep functions small and focused
- Use type hints where possible

### 2. Write Tests
- Add tests for new features
- Maintain 80%+ code coverage
- Run tests locally before pushing

```bash
cd quantum_admin
./run_tests.sh coverage
```

### 3. Run Code Quality Checks
```bash
# Format code
black backend/

# Lint
ruff check backend/

# Type check
mypy backend/ --ignore-missing-imports

# Security scan
bandit -r backend/
```

### 4. Commit Changes
```bash
# Stage changes
git add .

# Commit with meaningful message
git commit -m "feat: Add new feature X"
```

## 📝 Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
```
feat(auth): Add JWT token refresh endpoint

Implements automatic token refresh to improve UX.
Tokens now expire after 30 minutes but can be refreshed.

Closes #123
```

```
fix(docker): Handle connection timeout errors

Adds retry logic for Docker daemon connection failures.
Prevents crashes when Docker is temporarily unavailable.
```

## 🧪 Testing Guidelines

### Unit Tests
- Test individual functions/classes
- Mock external dependencies
- Fast execution (<1s per test)
- Located in `tests/unit/`

```python
def test_user_creation(test_db, user_factory):
    """Test creating a new user"""
    auth_service = AuthService(test_db)
    user_data = user_factory(username="testuser")

    user = auth_service.create_user(user_data)

    assert user.username == "testuser"
    assert user.is_active is True
```

### Integration Tests
- Test API endpoints
- Test component interaction
- Use test database
- Located in `tests/integration/`

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

### Coverage Requirements
- **Minimum**: 50% (CI will fail below this)
- **Target**: 80%+
- **New code**: Should have 90%+ coverage

## 🎨 Code Style

### Python
- Use **Black** for formatting (line length: 88)
- Use **Ruff** for linting
- Use **type hints** for function signatures
- Write **docstrings** for public functions

Example:
```python
def create_user(username: str, email: str) -> User:
    """
    Create a new user account

    Args:
        username: Unique username
        email: User email address

    Returns:
        Created User object

    Raises:
        ValueError: If username or email is invalid
    """
    if not username or not email:
        raise ValueError("Username and email required")

    # Implementation...
    return user
```

### JavaScript
- Use modern ES6+ syntax
- Async/await over callbacks
- Descriptive variable names
- JSDoc comments for functions

## 🔒 Security

### Security Guidelines
- Never commit secrets or credentials
- Use environment variables for sensitive data
- Validate all user input
- Use parameterized queries (no SQL injection)
- Follow OWASP Top 10 guidelines

### Reporting Security Issues
**Do not** create public GitHub issues for security vulnerabilities.

Instead:
1. Email: security@quantum-admin.example.com
2. Include: Detailed description and reproduction steps
3. We'll respond within 48 hours

## 📚 Documentation

### Code Documentation
- Add docstrings to all public functions/classes
- Use Google-style docstrings
- Include examples in docstrings when helpful

### Update Documentation
When adding features, update:
- `README.md` - If changing installation/usage
- `docs/` - API documentation
- `CHANGELOG.md` - List your changes

## 🔄 Pull Request Process

### Before Submitting
- [ ] All tests pass locally
- [ ] Code is formatted (black)
- [ ] No linting errors (ruff)
- [ ] Coverage is ≥ existing coverage
- [ ] Documentation is updated
- [ ] Commit messages follow convention

### Submitting
1. Push your branch to your fork
2. Create Pull Request on GitHub
3. Fill in the PR template
4. Link related issues

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] All tests passing

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings

## Related Issues
Closes #123
```

### Review Process
1. **Automated checks** run (CI/CD pipeline)
2. **Maintainer review** (may request changes)
3. **Approval** from at least 1 maintainer
4. **Merge** to main branch

## 🎯 Areas to Contribute

### High Priority
- [ ] Additional unit tests
- [ ] Integration tests for all endpoints
- [ ] Performance optimization
- [ ] Security improvements
- [ ] Documentation improvements

### Good First Issues
Look for issues tagged with `good-first-issue`:
- Simple bug fixes
- Documentation improvements
- Adding tests
- Code cleanup

### Feature Requests
Before implementing:
1. Check if issue exists
2. If not, create feature request issue
3. Discuss approach with maintainers
4. Get approval before implementing

## 💬 Getting Help

### Questions?
- GitHub Discussions
- Discord: [link]
- Email: help@quantum-admin.example.com

### Found a Bug?
1. Check if already reported
2. Create issue with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details
   - Error messages/logs

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive experience for everyone.

### Standards
- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Other unprofessional conduct

### Enforcement
Violations may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report violations to: conduct@quantum-admin.example.com

## 🏆 Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` - All contributors
- Release notes - Feature/fix credits
- GitHub insights - Contribution graphs

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Quantum Admin!** 🎉

Your contributions help make this project better for everyone.
