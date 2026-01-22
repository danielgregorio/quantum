# ⚛️ Quantum Admin

> **The Ultimate Enterprise Administration Interface**

Administration interface for Quantum Language projects with enterprise-grade features.

## ✨ Features

### 🔐 Authentication & Authorization
- **JWT Authentication**: Secure token-based auth with refresh tokens
- **RBAC System**: Role-Based Access Control (Admin, Developer, Viewer)
- **Session Management**: Track active sessions with IP and user-agent
- **Password Security**: bcrypt hashing with configurable rounds

### 🔌 Real-Time Updates
- **WebSocket Server**: Bidirectional real-time communication
- **Pub/Sub Messaging**: Channel-based event broadcasting
- **20+ Event Types**: Containers, tasks, deployments, system, metrics
- **Auto-Reconnect**: Exponential backoff for resilient connections

### 🔄 Jenkins Pipeline Designer
- **Visual Pipeline Editor**: `<q:pipeline>` XML abstraction
- **Jenkinsfile Generation**: Automatic conversion to Jenkinsfile
- **Built-in Templates**: Basic build, Docker deploy, parallel tests
- **Advanced Features**: Parallel stages, post-actions, parameters

### 🐳 Container Management
- **Visual Wizard**: Drag-and-drop container designer
- **12+ Templates**: PostgreSQL, MySQL, MongoDB, Redis, Nginx, LAMP, MEAN
- **Network Diagrams**: SVG visualization of container relationships
- **One-Click Deploy**: From design to running containers

### 📊 Performance & DevOps
- **Redis Caching**: Decorator-based caching layer
- **Celery Queue**: Background job processing
- **Rate Limiting**: Sliding window API rate limits
- **CI/CD Integration**: GitHub Actions, webhooks, environments

### 🎨 Modern UI
- **Dark Mode**: System-aware theme switching
- **Command Palette**: Cmd+K for quick navigation
- **AI Assistant**: RAG-powered help system
- **Multi-Language**: EN, PT-BR support

### 📈 Data Management
- **Multiple Databases**: SQLite, PostgreSQL, MySQL support
- **Visual Query Builder**: Drag-and-drop SQL queries
- **Chart Integration**: Chart.js visualization
- **Component Playground**: Live code editor

## 🚀 Quick Start

### ⚡ Interactive Installer (Recommended)

```bash
# From the quantum directory (parent of quantum_admin)
python3 install.py
```

The installer will guide you through:
1. ✅ System verification (Python, Docker, ports)
2. 🎯 Installation type (Full, Development, Custom)
3. 🗄️ Database configuration (SQLite, PostgreSQL, MySQL)
4. ⚡ Redis setup
5. 👤 Admin user creation
6. 📦 Automatic dependency installation
7. ⚙️ Environment file generation

**See:** [../INSTALL.md](../INSTALL.md) for detailed installation guide.

---

### 📋 Manual Installation

If you prefer manual installation:

#### 1. Install Dependencies

```bash
cd quantum_admin
pip install -r requirements.txt
```

#### 2. Configure Environment

Create `.env` file in the root directory:

```bash
DATABASE_URL=sqlite:///quantum_admin.db
JWT_SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

#### 3. Run the Server

```bash
# From the quantum_admin/backend directory
python main.py

# Or using the management CLI
cd .. && python quantum-cli.py start
```

The API will be available at `http://localhost:8000`

#### 4. Access the Interface

- **Login Page**: http://localhost:8000/static/login.html
- **Dashboard**: http://localhost:8000/static/index.html
- **API Docs**: http://localhost:8000/docs
- **Pipeline Editor**: http://localhost:8000/static/pipeline-editor.html
- **Container Wizard**: http://localhost:8000/static/container-wizard.html

## Project Structure

```
quantum_admin/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # SQLAlchemy models
│   ├── database.py      # Database configuration
│   ├── crud.py          # Database operations
│   ├── schemas.py       # Pydantic schemas
│   ├── docker_service.py # Docker container management
│   └── requirements.txt
├── frontend/            # Future: React/Alpine.js UI
├── projects/            # Project data storage
├── run.py               # Application launcher
└── quantum_admin.db     # SQLite database (auto-created)
```

## API Endpoints

### Projects

- `GET /projects` - List all projects
- `POST /projects` - Create a new project
- `GET /projects/{id}` - Get project details
- `PUT /projects/{id}` - Update a project
- `DELETE /projects/{id}` - Delete a project

### Datasources

- `GET /projects/{id}/datasources` - List datasources for a project
- `POST /projects/{id}/datasources` - Create a new datasource (with Docker container)

### Docker Container Management

- `POST /datasources/{id}/start` - Start a datasource container
- `POST /datasources/{id}/stop` - Stop a datasource container
- `POST /datasources/{id}/restart` - Restart a datasource container
- `GET /datasources/{id}/status` - Get detailed container status
- `GET /datasources/{id}/logs?lines=100` - Get container logs
- `GET /docker/containers?all=true` - List all Docker containers

### Components

- `GET /projects/{id}/components` - List components for a project

### Endpoints

- `GET /projects/{id}/endpoints` - List API endpoints for a project

## Example Usage

### Create a Project

```bash
curl -X POST "http://localhost:8000/projects" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "description": "My Quantum application"}'
```

### List Projects

```bash
curl "http://localhost:8000/projects"
```

### Get Project Details

```bash
curl "http://localhost:8000/projects/1"
```

### Create a Docker Datasource

```bash
curl -X POST "http://localhost:8000/projects/1/datasources" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "main-db",
    "type": "postgres",
    "connection_type": "docker",
    "image": "postgres:16-alpine",
    "port": 5432,
    "database_name": "mydb",
    "username": "admin",
    "password": "secret",
    "auto_start": true
  }'
```

### Start a Database Container

```bash
curl -X POST "http://localhost:8000/datasources/1/start"
```

### Check Container Status

```bash
curl "http://localhost:8000/datasources/1/status"
```

### View Container Logs

```bash
curl "http://localhost:8000/datasources/1/logs?lines=50"
```

## Development

### Database Schema

The SQLite database includes these tables:

- **projects**: Project metadata
- **datasources**: Database connections (Docker/direct)
- **migrations**: Schema migration tracking
- **components**: Component status tracking
- **endpoints**: REST API endpoint definitions

### Adding New Features

1. Update `models.py` for new database tables
2. Add CRUD operations to `crud.py`
3. Define request/response schemas in `schemas.py`
4. Implement API endpoints in `main.py`

## Next Steps

- [x] Add Docker container management
- [ ] Implement password encryption
- [ ] Build frontend UI
- [ ] Add component scanning
- [ ] Implement hot reload (SSE)
- [ ] Add migration system

## Docker Support

Quantum Admin supports managing database containers for:
- **PostgreSQL** (postgres:16-alpine, postgres:15-alpine, etc.)
- **MySQL** (mysql:8.0, mysql:5.7, etc.)
- **MariaDB** (mariadb:11.2, mariadb:10.11, etc.)
- **MongoDB** (mongo:7.0, mongo:6.0, etc.)
- **Redis** (redis:7.2-alpine, redis:6.2-alpine, etc.)

Containers are automatically configured with:
- Auto-generated connection strings
- Environment variables for credentials
- Port mapping to host
- Restart policies
- Health monitoring

## License

MIT
