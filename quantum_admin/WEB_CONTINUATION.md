# Claude Code Web - Continuation Prompt

**Date**: 2025-01-06
**Repository**: https://github.com/danielgregorio/quantum
**Branch**: main
**Task**: Continue Quantum Admin v2.0 Development

---

## 🎯 **Your Mission**

You are continuing development of **Quantum Admin**, an administration interface for Quantum Language projects. The backend and frontend v1.0 are **100% complete and functional**. Your job is to implement the **missing features** documented in the roadmap.

---

## 📁 **Project Structure & Key Files**

### **Documentation (START HERE)** 📚

Located in: `quantum_admin/`

1. **`ROADMAP.md`** (400+ lines) - **READ THIS FIRST**
   - Complete implementation roadmap
   - What's already implemented (v1.0 - 100% complete)
   - What's missing (8 features at 0-30% completion)
   - Detailed architecture for each feature
   - Code examples for service implementations
   - Database schema additions
   - API endpoint specifications
   - 4-week implementation plan (3 options: Test-focused, Deploy-focused, Balanced)

2. **`CURRENT_STATE.md`** (200+ lines) - **Quick Reference**
   - Condensed current state analysis
   - Feature priority matrix (P0, P1, P2, P3)
   - Quick start commands to test existing features
   - Known issues and limitations
   - Key files reference table

3. **`README.md`** - **Getting Started Guide**
   - Installation instructions
   - API documentation overview
   - Example curl commands
   - Docker support information

---

### **Backend (Fully Functional)** ✅

Located in: `quantum_admin/backend/`

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `main.py` | 790 | FastAPI app, all endpoints | ✅ Complete |
| `models.py` | 128 | SQLAlchemy models (5 tables) | ✅ Complete |
| `docker_service.py` | 396 | Docker container management | ✅ Complete |
| `db_setup_service.py` | 194 | Database auto-setup | ✅ Complete |
| `crud.py` | 257 | CRUD operations | ✅ Complete |
| `schemas.py` | 135 | Pydantic validation schemas | ✅ Complete |
| `database.py` | 46 | Database configuration | ✅ Complete |

**What's implemented:**
- 30+ RESTful API endpoints
- SQLite database with 5 models:
  - `Project`: Quantum projects
  - `Datasource`: Database connections (Docker/direct)
  - `Migration`: Schema migration tracking
  - `Component`: .q file tracking
  - `Endpoint`: REST endpoint definitions
- Full CRUD for all resources
- Docker container lifecycle (create, start, stop, restart, remove, logs)
- Database auto-setup with retry logic (PostgreSQL, MySQL, MariaDB, MongoDB, Redis)
- Port conflict auto-resolution
- Health monitoring

---

### **Frontend (Fully Functional)** ✅

Located in: `quantum_admin/frontend/`

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `index.html` | 726 | Alpine.js UI | ✅ Complete |

**What's implemented:**
- Project management (create, list, delete, select)
- Datasource management with **Express Mode** (1-click database creation)
- Advanced mode for granular control
- Container controls (start, stop, restart, view logs)
- Real-time status polling (2-second intervals)
- Status badges (running, configuring, ready, error, stopped)
- Log viewer modal
- Responsive Tailwind CSS design

---

### **Test Infrastructure** ✅

Located in: `examples/` (test files) and root (test runner)

- **`test_runner.py`**: 97 automated tests across 19 test suites
- **Test files**: `examples/test-*.q` (97 files covering all 12 Quantum phases)
- **Status**: All tests passing (100%)

**Note**: Test infrastructure exists but has **NO API integration yet** - this is one of your tasks!

---

## 🚀 **How to Get Started**

### **Step 1: Read the Documentation**

```bash
# In the repository root:
cd quantum_admin

# Read these files in order:
1. CURRENT_STATE.md    # Quick overview (5 min read)
2. ROADMAP.md          # Detailed plan (15 min read)
3. README.md           # Getting started (5 min read)
```

### **Step 2: Start the Existing Backend**

```bash
cd quantum_admin
python run.py

# Server starts at: http://localhost:8000
# Swagger docs at: http://localhost:8000/docs
# Frontend UI at:  http://localhost:8000/
```

### **Step 3: Test Current Features**

**Test Project Creation:**
```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "test-project", "description": "Testing"}'
```

**Test Datasource Creation (Docker PostgreSQL):**
```bash
curl -X POST http://localhost:8000/projects/1/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-db",
    "type": "postgres",
    "connection_type": "docker",
    "image": "postgres:16-alpine",
    "port": 5432,
    "database_name": "testdb",
    "username": "admin",
    "password": "secret",
    "auto_start": true
  }'
```

**Start Container:**
```bash
curl -X POST http://localhost:8000/datasources/1/start
```

**View Logs:**
```bash
curl http://localhost:8000/datasources/1/logs?lines=50
```

### **Step 4: Choose Your Implementation Path**

Read `ROADMAP.md` section "🎯 Recommended Implementation Roadmap" and choose:

**Option A: Test-Focused** (Fastest to value)
- Week 1: Test Execution Integration
- Week 2: Configuration Management
- Week 3: Deploy Automation
- Week 4: CI/CD Integration

**Option B: Deploy-Focused** (Maximum impact)
- Week 1: Configuration Management + Security
- Week 2: Deploy Automation
- Week 3: Test Execution Integration
- Week 4: CI/CD Integration

**Option C: Balanced** ⭐ **RECOMMENDED**
- Week 1: Test Execution + Config Management (parallel)
- Week 2: Deploy Automation
- Week 3: CI/CD Integration
- Week 4: Polish + Real-time features

---

## 📋 **What You Need to Implement**

### **Priority 0 (Must Have) - Week 1-2**

#### 1. **Test Execution Integration** (0% complete)
**Location**: Create new files in `quantum_admin/backend/`

**Files to create:**
- `backend/test_execution_service.py` - Service to run test_runner.py
- Add to `backend/models.py`: TestRun, TestResult models
- Add to `backend/schemas.py`: TestRun, TestResult schemas
- Add to `backend/main.py`: Test execution endpoints

**Endpoints to add:**
```python
POST   /api/projects/{id}/tests/run          # Execute tests
GET    /api/projects/{id}/tests/runs         # List test runs
GET    /api/projects/{id}/tests/runs/{id}    # Get test details
GET    /api/projects/{id}/tests/runs/{id}/status  # Real-time status
POST   /api/projects/{id}/tests/runs/{id}/cancel # Cancel test
```

**Frontend to create:**
- `frontend/tests.html` - Test execution UI

**Reference**: See `ROADMAP.md` section "Test Execution Service Architecture" for code examples.

---

#### 2. **Configuration Management** (20% complete)
**Location**: Extend existing files + create new

**Files to create:**
- `backend/secret_manager.py` - Encryption for passwords/secrets
- Add to `backend/models.py`: EnvironmentVariable, ConfigurationHistory models

**Endpoints to add:**
```python
GET    /api/projects/{id}/config              # Get project config
PUT    /api/projects/{id}/config              # Update config
GET    /api/projects/{id}/environment-variables  # List env vars
POST   /api/projects/{id}/environment-variables  # Create env var
PUT    /api/projects/{id}/environment-variables/{key}  # Update
DELETE /api/projects/{id}/environment-variables/{key}  # Delete
GET    /api/projects/{id}/secrets             # List secrets (masked)
POST   /api/projects/{id}/secrets             # Create secret
GET    /api/projects/{id}/config/history      # Config history
```

**Security implementation:**
```python
# Use Fernet symmetric encryption
from cryptography.fernet import Fernet
import os

ENCRYPTION_KEY = os.getenv('QUANTUM_ENCRYPTION_KEY')
cipher = Fernet(ENCRYPTION_KEY)

def encrypt_password(password: str) -> str:
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

**Frontend to create:**
- `frontend/config.html` - Configuration editor UI

**Reference**: See `ROADMAP.md` section "Configuration Management" for full specifications.

---

### **Priority 1 (Should Have) - Week 2-3**

#### 3. **Deploy Automation** (0% complete)
**Location**: Create new deployment system

**Files to create:**
- `backend/deployment_service.py` - Build, push, release, rollback
- Add to `backend/models.py`: Environment, Build, Deployment models

**Endpoints to add:**
```python
POST   /api/projects/{id}/deploy/build        # Build artifacts
POST   /api/projects/{id}/deploy/push         # Push to registry
POST   /api/projects/{id}/deploy/release      # Deploy to environment
POST   /api/projects/{id}/deploy/rollback     # Rollback deployment
GET    /api/projects/{id}/deployments         # List deployments
GET    /api/projects/{id}/deployments/{id}    # Get deployment details
GET    /api/projects/{id}/environments        # List environments
POST   /api/projects/{id}/environments        # Create environment
GET    /api/projects/{id}/deployments/{id}/logs  # Stream logs (SSE)
```

**Frontend to create:**
- `frontend/deploy.html` - Deployment dashboard UI

**Reference**: See `ROADMAP.md` section "Deployment Service Architecture" for implementation details.

---

### **Priority 2 (Good to Have) - Week 3-4**

#### 4. **CI/CD Pipeline Integration** (0% complete)
**Location**: Create CI/CD integration system

**Files to create:**
- `backend/cicd_service.py` - GitHub Actions, webhook handling
- Add to `backend/models.py`: CICDIntegration, Pipeline, PipelineStage models

**Endpoints to add:**
```python
POST   /api/projects/{id}/cicd/github/setup    # Setup GitHub integration
POST   /api/webhooks/github                    # Webhook receiver
GET    /api/projects/{id}/cicd/pipelines       # List pipelines
GET    /api/projects/{id}/cicd/pipelines/{id}  # Pipeline details
GET    /api/projects/{id}/cicd/pipelines/{id}/logs  # Stream logs
POST   /api/projects/{id}/cicd/pipelines/{id}/retry   # Retry pipeline
POST   /api/projects/{id}/cicd/pipelines/{id}/cancel  # Cancel pipeline
GET    /api/projects/{id}/cicd/status          # Current CI/CD status
```

**Frontend to create:**
- `frontend/cicd.html` - Pipeline monitoring UI

**Reference**: See `ROADMAP.md` section "CI/CD Integration Architecture" for webhook handling.

---

## 🛠️ **Development Guidelines**

### **Code Style**
- Follow existing patterns in `backend/main.py`
- Use SQLAlchemy models from `backend/models.py`
- Use Pydantic schemas for validation
- Add docstrings to all functions
- Use type hints

### **Database Changes**
- Add new models to `backend/models.py`
- Database migrations happen automatically (SQLAlchemy creates tables)
- Run `init_db()` on startup (already configured in `main.py`)

### **API Endpoint Pattern**
```python
@app.post("/api/resource", response_model=schemas.ResourceResponse, tags=["Resources"])
def create_resource(
    resource: schemas.ResourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new resource"""
    try:
        new_resource = crud.create_resource(db, **resource.dict())
        return new_resource
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### **Service Layer Pattern**
```python
class MyService:
    """Service for handling business logic"""

    @staticmethod
    def do_something(param: str) -> Result:
        """
        Perform business operation

        Args:
            param: Description

        Returns:
            Result object

        Raises:
            ValueError: If validation fails
        """
        # Implementation
        pass
```

### **Testing**
- Test endpoints manually using Swagger UI at `/docs`
- Add integration tests in `examples/test-*.q` if applicable
- Use `curl` commands to verify functionality

---

## 🔍 **Important Notes**

### **Current Limitations (Known Issues)**
1. ⚠️ **Passwords in plain text** - TODO in `main.py` line 346
2. ⚠️ **Polling instead of SSE** - Frontend polls every 2 seconds
3. ⚠️ **No authentication** - All endpoints are public
4. ⚠️ **SQLite in production** - Should switch to PostgreSQL for concurrent writes

### **Dependencies Already Installed**
Check `backend/requirements.txt` for installed packages:
- fastapi
- uvicorn
- sqlalchemy
- docker
- psycopg2-binary (PostgreSQL)
- pymysql (MySQL)
- pymongo (MongoDB)

**You'll need to add:**
- `cryptography` (for password encryption)
- `python-jose` (for JWT authentication)
- `sse-starlette` (for Server-Sent Events)
- `celery` + `redis` (optional, for task queue)

---

## 📊 **Success Criteria**

### **Phase 1 (Test Execution + Config) - Week 1**
- [ ] Can execute all 97 tests from UI
- [ ] Test results displayed with pass/fail status
- [ ] Historical test runs tracked (last 100)
- [ ] All passwords encrypted in database
- [ ] Environment variables manageable from UI
- [ ] Config changes tracked with history

### **Phase 2 (Deploy Automation) - Week 2**
- [ ] Can build project artifacts
- [ ] Can deploy to 3+ environment types
- [ ] Rollback works within 30 seconds
- [ ] Deployment logs streamed in real-time
- [ ] Build artifacts stored securely

### **Phase 3 (CI/CD Integration) - Week 3**
- [ ] GitHub integration works end-to-end
- [ ] Webhooks trigger tests automatically
- [ ] Pipeline status visible in UI
- [ ] Can retry failed pipelines
- [ ] Pipeline logs accessible

### **Phase 4 (Polish) - Week 4**
- [ ] SSE replaces polling
- [ ] JWT authentication working
- [ ] Component scanning implemented
- [ ] Migration system UI complete

---

## 🚦 **Your First Steps (Action Items)**

1. **Clone/pull the repository** (if not already done)
   ```bash
   git clone https://github.com/danielgregorio/quantum.git
   cd quantum
   ```

2. **Read the documentation**
   ```bash
   cd quantum_admin
   cat CURRENT_STATE.md    # 5 minutes
   cat ROADMAP.md          # 15 minutes
   ```

3. **Start the backend**
   ```bash
   python run.py
   # Visit http://localhost:8000/docs
   ```

4. **Test existing features**
   - Create a project via Swagger UI
   - Create a datasource (Express Mode)
   - Start container and view logs
   - Verify everything works

5. **Choose implementation path**
   - Recommend: **Option C (Balanced)**
   - Start with Test Execution Integration
   - Then Config Management + Password Encryption

6. **Create first service**
   ```bash
   # Create backend/test_execution_service.py
   # Follow the pattern in ROADMAP.md
   # Add TestRun/TestResult models
   # Add API endpoints to main.py
   ```

7. **Test and iterate**
   - Use Swagger UI to test endpoints
   - Create frontend UI incrementally
   - Commit frequently with good messages

---

## 💡 **Tips for Success**

1. **Start small**: Implement one endpoint at a time
2. **Test frequently**: Use Swagger UI after each endpoint
3. **Follow patterns**: Copy existing code structure from `main.py`
4. **Read ROADMAP.md**: All architecture decisions are documented
5. **Commit often**: Use conventional commits (feat:, fix:, chore:, docs:)
6. **Ask questions**: If architecture is unclear, refer to ROADMAP.md examples

---

## 📞 **Reference Files Summary**

| File | Purpose | When to Read |
|------|---------|--------------|
| `quantum_admin/ROADMAP.md` | Detailed implementation plan | Before starting each phase |
| `quantum_admin/CURRENT_STATE.md` | Quick reference, priorities | Daily reference |
| `quantum_admin/README.md` | Getting started, API examples | When setting up |
| `quantum_admin/backend/main.py` | API endpoint patterns | When adding endpoints |
| `quantum_admin/backend/models.py` | Database model patterns | When adding models |
| `quantum_admin/backend/docker_service.py` | Service layer example | When creating services |
| `quantum_admin/frontend/index.html` | UI patterns | When creating frontend |

---

## 🎯 **Your Goal**

Transform Quantum Admin from **v1.0 (backend + datasource management)** to **v2.0 (full DevOps platform)** by implementing:

1. ✅ Test execution and monitoring
2. ✅ Configuration and secrets management
3. ✅ Deployment automation
4. ✅ CI/CD pipeline integration

**All the architecture is documented. All the patterns exist. You just need to implement following the roadmap!**

Good luck! 🚀

---

**Last Updated**: 2025-01-06
**Repository**: https://github.com/danielgregorio/quantum
**Branch**: main
**Status**: Ready for implementation
