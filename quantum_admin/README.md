# Quantum Admin

Administration interface for Quantum Language projects.

## Features

- **Project Management**: Create, update, and manage Quantum projects
- **Infrastructure Connectors**: Database, MQ, Cache, Storage, AI providers
- **Docker Container Management**: Create, start, stop, restart containers
- **Settings Management**: YAML-based configuration with environment resolution
- **User Authentication**: JWT-based auth with role support
- **Dark Theme UI**: Modern semantic CSS without Tailwind

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

# Or with uvicorn directly
cd quantum_admin && python -m uvicorn backend.main:app --port 8001 --reload
```

The admin UI will be available at `http://localhost:8001/admin`

**Default credentials**: `admin` / `admin`

### 3. Access API Documentation

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## Project Structure

```
quantum_admin/
├── backend/
│   ├── main.py              # FastAPI application (79 endpoints)
│   ├── models.py            # SQLAlchemy models (11 models)
│   ├── database.py          # Database configuration
│   ├── crud.py              # Database operations
│   ├── schemas.py           # Pydantic schemas
│   ├── docker_service.py    # Docker container management
│   ├── connector_service.py # Infrastructure connectors (flagship)
│   ├── settings_service.py  # YAML configuration
│   ├── auth_service.py      # JWT authentication
│   └── requirements.txt
├── static/
│   └── quantum-admin.css    # Dark theme CSS
├── settings/
│   ├── global.yaml          # Global configuration
│   └── connectors.yaml      # Connector definitions
├── run.py                   # Application launcher
└── quantum_admin.db         # SQLite database (auto-created)
```

## Key Endpoints

### Authentication
- `POST /auth/login` - JWT login
- `GET /auth/me` - Current user info

### Projects
- `GET /projects` - List all projects
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project details

### Connectors (Infrastructure)
- `GET /settings/connectors` - List all connectors
- `POST /settings/connectors` - Create connector
- `POST /settings/connectors/{id}/test` - Test connection
- `POST /settings/connectors/{id}/docker/start` - Start Docker container

### Docker
- `GET /docker/status` - Docker connection status
- `GET /docker/containers` - List containers
- `POST /docker/containers/{id}/start` - Start container
- `GET /docker/containers/{id}/logs` - View logs

### Settings
- `GET /settings` - Get all settings
- `PUT /settings` - Update settings

## Supported Connectors

| Type | Providers |
|------|-----------|
| **Database** | PostgreSQL, MySQL, MariaDB, MongoDB, SQLite |
| **Message Queue** | RabbitMQ, Redis Queue, Kafka |
| **Cache** | Redis, Memcached |
| **Storage** | S3, MinIO, Local |
| **AI** | Ollama, LMStudio, Anthropic, OpenAI, OpenRouter |

## License

MIT
