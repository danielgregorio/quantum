# Quantum Admin - CI/CD Pipeline

Automated testing, security scanning, and deployment pipeline.

## 🔄 Pipeline Overview

```
┌─────────────┐
│   Push/PR   │
└──────┬──────┘
       │
       ├─────────┬─────────┬─────────┬─────────┐
       │         │         │         │         │
       ▼         ▼         ▼         ▼         ▼
   ┌──────┐ ┌────────┐ ┌───────┐ ┌───────┐ ┌────────┐
   │ Lint │ │Security│ │ Tests │ │ Build │ │Summary │
   └───┬──┘ └────┬───┘ └───┬───┘ └───┬───┘ └────┬───┘
       │         │         │         │         │
       └─────────┴─────────┴─────────┴─────────┘
                         │
                         ▼
                  ┌────────────┐
                  │   Deploy   │ (main branch only)
                  └────────────┘
```

## 📋 Pipeline Jobs

### 1. Code Quality (`lint`)
Ensures code meets quality standards:
- **Black**: Code formatting check
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking

**Runs on**: All pushes and PRs
**Can fail**: No (warnings only)

### 2. Security Scan (`security`)
Identifies security vulnerabilities:
- **Bandit**: Security linter for Python code
- **Safety**: Checks dependencies for known vulnerabilities

**Runs on**: All pushes and PRs
**Can fail**: No (informational)
**Artifacts**: `bandit-report.json`

### 3. Tests (`test`)
Comprehensive test suite:
- **Unit tests**: Fast, isolated component tests
- **Integration tests**: API endpoint tests
- **Coverage**: Minimum 50% required

**Matrix**: Python 3.10, 3.11, 3.12
**Runs on**: All pushes and PRs
**Can fail**: Yes ✅ (blocks merge if failing)
**Artifacts**: Coverage reports (HTML + XML)

### 4. Coverage Report (`coverage`)
Generates detailed coverage analysis:
- HTML coverage report
- Comments on PRs with coverage changes
- Enforces minimum coverage thresholds:
  - 🟢 Green: ≥80%
  - 🟠 Orange: ≥50%
  - 🔴 Red: <50%

**Runs on**: All pushes and PRs
**Depends on**: `test`

### 5. Build Check (`build`)
Validates application can start:
- Checks imports
- Verifies FastAPI app creation
- Ensures no startup errors

**Runs on**: All pushes and PRs
**Depends on**: `lint`, `test`
**Can fail**: Yes ✅

### 6. Deploy (`deploy`)
Deploys to production:
- **Triggers**: Only on `main` branch push
- **Requires**: All previous jobs pass
- **Environment**: Production (requires approval)

**Runs on**: `main` branch only
**Manual approval**: Required

### 7. Summary (`summary`)
Aggregates results and reports status:
- Shows all job results
- Fails if tests failed
- Provides quick overview

**Runs on**: Always (even if previous jobs fail)

## 🚀 Triggering the Pipeline

### Automatic Triggers
- **Push to any branch**: Runs full pipeline (except deploy)
- **Push to `main`**: Runs full pipeline including deploy
- **Pull Request**: Runs full pipeline, comments on PR
- **Branch pattern `claude/**`**: Runs full pipeline

### Manual Trigger
```bash
# Via GitHub UI:
Actions → Quantum Admin CI/CD → Run workflow

# Via GitHub CLI:
gh workflow run ci.yml --ref main
```

## 📊 Status Badges

Add to README.md:

```markdown
![CI/CD](https://github.com/danielgregorio/quantum/workflows/Quantum%20Admin%20CI%2FCD/badge.svg)
![Coverage](https://codecov.io/gh/danielgregorio/quantum/branch/main/graph/badge.svg)
```

## 🔐 Required Secrets

For deployment, configure these in GitHub Settings → Secrets:

```
DEPLOY_HOST         # Production server hostname
DEPLOY_USER         # SSH username
DEPLOY_KEY          # SSH private key
CODECOV_TOKEN       # Codecov.io token (optional)
```

## 📝 Configuration Files

### `.github/workflows/ci.yml`
Main CI/CD pipeline configuration

### `quantum_admin/pytest.ini`
Test configuration and coverage settings

### `quantum_admin/requirements-admin.txt`
Python dependencies

## 🧪 Running Locally

Before pushing, run the same checks locally:

```bash
# Code quality
black --check quantum_admin/backend/
ruff check quantum_admin/backend/
mypy quantum_admin/backend/

# Security
bandit -r quantum_admin/backend/
safety check

# Tests
cd quantum_admin
./run_tests.sh coverage
```

## 🛠️ Customization

### Modify Python Versions
Edit `.github/workflows/ci.yml`:
```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']
```

### Change Coverage Threshold
Edit `quantum_admin/pytest.ini`:
```ini
addopts =
    --cov-fail-under=80  # Change from 50 to 80
```

### Add More Tests
Create new test files in:
- `quantum_admin/tests/unit/`
- `quantum_admin/tests/integration/`
- `quantum_admin/tests/e2e/`

## 📈 Metrics & Reporting

### Code Coverage
- Tracked by Codecov.io
- Visible in PR comments
- Historical trends available

### Test Results
- Displayed in GitHub Actions UI
- Downloadable as artifacts
- Retained for 90 days

### Security Reports
- Bandit JSON report
- Safety vulnerability list
- Uploaded as artifacts

## 🔄 Continuous Deployment

### Current Setup
- Deploys to production on `main` push
- Requires all checks to pass
- Manual approval required

### Future Enhancements
- [ ] Blue-green deployment
- [ ] Canary releases
- [ ] Automatic rollback on errors
- [ ] Slack/Discord notifications
- [ ] Performance testing
- [ ] E2E tests in CI

## 📚 Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Bandit Security](https://bandit.readthedocs.io/)

## 🐛 Troubleshooting

### Pipeline Failing?
1. Check the logs in GitHub Actions
2. Run tests locally: `./run_tests.sh`
3. Verify dependencies: `pip install -r requirements-admin.txt`

### Coverage Too Low?
1. Check coverage report: `htmlcov/index.html`
2. Add tests for uncovered code
3. Run: `pytest --cov=backend --cov-report=html`

### Deployment Failing?
1. Check deployment logs
2. Verify secrets are configured
3. Test SSH connection manually
4. Check server disk space/resources

---

**Pipeline Status**: ✅ Active and running on every push!
