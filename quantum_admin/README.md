# Quantum Admin

Administration interface for Quantum Language projects.

## Features

- **Project Management**: Create, update, and manage Quantum projects
- **Datasource Management**: Configure database connections (Docker or direct)
- **Docker Container Management**: Create, start, stop, restart database containers
- **Container Monitoring**: View container status, logs, and health
- **Component Tracking**: Monitor component status and compilation
- **API Endpoints**: View and manage REST API endpoints
- **SQLite Database**: Zero-configuration local database

## Quick Start

### 1. Install Dependencies

```bash
cd quantum_admin/backend
pip install -r requirements.txt
```

### 2. Run the Server

```bash
# From the quantum_admin directory
python run.py
```

The API will be available at `http://localhost:8000`

**Note**: Docker Desktop must be running for datasource container management features.

### 3. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

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
