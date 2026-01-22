"""
RAG (Retrieval-Augmented Generation) System for Quantum AI
Indexes Quantum framework documentation, intents, and best practices
"""

import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path


class QuantumRAG:
    """
    RAG system calibrated for Quantum framework
    Retrieves relevant context for AI responses
    """

    def __init__(self):
        self.knowledge_base = self._build_knowledge_base()
        self.intent_patterns = self._load_intent_patterns()

    def _build_knowledge_base(self) -> List[Dict[str, Any]]:
        """Build comprehensive knowledge base"""
        return [
            # Databinding
            {
                "id": "databinding-basics",
                "category": "databinding",
                "keywords": ["databinding", "binding", "variable", "{}", "expression", "context"],
                "title": "Databinding Basics",
                "content": """
Quantum uses curly braces {} for databinding expressions:

**Simple variables**: {username}, {email}
**Object properties**: {user.name}, {user.email}
**Array access**: {items[0]}, {users[index]}
**Nested**: {user.address.city}

Context variables automatically available:
- {session} - Session data
- {user} - Logged in user
- {isLoggedIn} - Authentication status
- {request} - Request information

Example:
<p>Hello, {user.name}!</p>
<p>You have {notifications.length} new messages</p>
""",
                "examples": [
                    "{user.name}",
                    "{items[0].title}",
                    "{session.isLoggedIn}"
                ]
            },

            # Components
            {
                "id": "component-structure",
                "category": "components",
                "keywords": ["component", "structure", "xml", "create", "template"],
                "title": "Component Structure",
                "content": """
Basic Quantum component structure:

<?quantum version="1.0"?>
<component name="mycomp">
    <h1>Hello, {name}!</h1>
    <p>This is a Quantum component</p>
</component>

Best practices:
- Use descriptive component names
- Keep components focused (single responsibility)
- Pass data via context variables
- Reuse components with <include>
""",
                "examples": [
                    '<component name="hello">...</component>',
                    '<include src="header.q" />'
                ]
            },

            # Loops
            {
                "id": "loops",
                "category": "loops",
                "keywords": ["loop", "iterate", "array", "foreach", "repeat"],
                "title": "Loops and Iteration",
                "content": """
Use <loop> to iterate over arrays:

<loop array="users">
    <div class="user-card">
        <h3>{item.name}</h3>
        <p>{item.email}</p>
    </div>
</loop>

Available variables inside loop:
- {item} - Current item
- {index} - Current index (0-based)
- {isFirst} - True for first item
- {isLast} - True for last item

Nested loops:
<loop array="categories">
    <h2>{item.name}</h2>
    <loop array="item.products">
        <p>{item.name}</p>
    </loop>
</loop>
""",
                "examples": [
                    '<loop array="items">{item}</loop>',
                    '<loop array="users"><p>{index}: {item.name}</p></loop>'
                ]
            },

            # Conditionals
            {
                "id": "conditionals",
                "category": "conditionals",
                "keywords": ["if", "conditional", "condition", "else", "ternary"],
                "title": "Conditional Rendering",
                "content": """
Use <if> for conditional rendering:

<if condition="{isLoggedIn}">
    <p>Welcome back, {user.name}!</p>
</if>

<if condition="{user.role == 'admin'}">
    <button>Admin Panel</button>
</if>

Operators supported:
- ==, != - Equality
- >, <, >=, <= - Comparison
- and, or - Logical operators

Examples:
<if condition="{score >= 90}">Grade: A</if>
<if condition="{user.isPremium and user.isActive}">Premium Active</if>
""",
                "examples": [
                    '<if condition="{isAdmin}">Admin content</if>',
                    '<if condition="{count > 0}">You have items</if>'
                ]
            },

            # Database
            {
                "id": "database-queries",
                "category": "database",
                "keywords": ["database", "query", "sql", "datasource", "crud"],
                "title": "Database Operations",
                "content": """
Database operations in Quantum:

1. Create a datasource in Admin UI
2. Use <query> element:

<query name="getUsers" datasource="mydb">
    SELECT * FROM users WHERE active = true
</query>

<loop array="getUsers">
    <p>{item.username}</p>
</loop>

Best practices:
- Always use parameterized queries
- Limit results with LIMIT clause
- Handle errors gracefully
- Use connection pooling

Security:
- NEVER concatenate user input into queries
- Use parameter binding
- Validate all inputs
- Implement proper access control
""",
                "examples": [
                    '<query name="users" datasource="db">SELECT * FROM users</query>',
                    '<loop array="users">{item.name}</loop>'
                ]
            },

            # Services
            {
                "id": "services",
                "category": "services",
                "keywords": ["service", "email", "file", "upload", "action"],
                "title": "Quantum Services",
                "content": """
Available services in Quantum:

**DatabaseService**: Execute queries, transactions
**EmailService**: Send emails, templates
**FileUploadService**: Handle file uploads
**AuthService**: Authentication, sessions
**ActionHandler**: Custom server-side logic

Example usage:
<action name="sendEmail" service="email">
    <param name="to">{user.email}</param>
    <param name="subject">Welcome!</param>
    <param name="body">Hello {user.name}</param>
</action>

File uploads:
<form action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="file" />
    <button type="submit">Upload</button>
</form>
""",
                "examples": [
                    '<action name="send" service="email">...</action>',
                    '<input type="file" name="upload" />'
                ]
            },

            # Security
            {
                "id": "security-practices",
                "category": "security",
                "keywords": ["security", "xss", "sql injection", "csrf", "auth"],
                "title": "Security Best Practices",
                "content": """
Security guidelines for Quantum:

**Input Validation**:
- Always validate user input
- Sanitize before database operations
- Use parameterized queries

**Output Encoding**:
- Quantum auto-escapes HTML by default
- Be careful with raw output
- Validate file uploads

**Authentication**:
- Use AuthService for user management
- Implement session timeout
- Enable HTTPS in production
- Consider 2FA for sensitive data

**CSRF Protection**:
- Use CSRF tokens in forms
- Validate origin headers
- Implement SameSite cookies

**Common Vulnerabilities to Avoid**:
- SQL Injection: Use parameterized queries
- XSS: Don't use raw HTML from users
- Path Traversal: Validate file paths
- Insecure Deserialization: Validate JSON input
""",
                "examples": [
                    "Parameterized: SELECT * FROM users WHERE id = ?",
                    "CSRF Token: <input type=\"hidden\" name=\"csrf_token\" value=\"{csrf}\" />"
                ]
            },

            # Performance
            {
                "id": "performance",
                "category": "performance",
                "keywords": ["performance", "optimization", "cache", "speed", "slow"],
                "title": "Performance Optimization",
                "content": """
Performance tips for Quantum:

**Query Optimization**:
- Use LIMIT to restrict result sets
- Add indexes on frequently queried columns
- Avoid N+1 query problems
- Use connection pooling

**Caching**:
- Enable query result caching
- Cache expensive computations
- Use CDN for static assets

**Component Optimization**:
- Keep components small and focused
- Avoid deep nesting
- Minimize loop iterations
- Lazy load heavy components

**Monitoring**:
- Use Admin UI monitoring
- Track slow queries
- Monitor memory usage
- Set up alerts for issues
""",
                "examples": [
                    "SELECT * FROM users LIMIT 100",
                    "CREATE INDEX idx_email ON users(email)"
                ]
            },

            # Schema Inspector
            {
                "id": "schema-inspector",
                "category": "schema",
                "keywords": ["schema", "inspect", "erd", "diagram", "database structure", "tables", "columns"],
                "title": "Database Schema Inspector",
                "content": """
Quantum Admin includes a powerful Schema Inspector for analyzing databases:

**Features**:
- Visual ERD (Entity-Relationship Diagram) generation
- Table and column inspection
- Relationship mapping (foreign keys)
- Multiple export formats (Mermaid, DBML, Graphviz DOT, JSON)
- SQLAlchemy model generation from existing databases

**API Endpoints**:
- GET /schema/inspect - Get complete database schema
- GET /schema/models - Generate SQLAlchemy model code
- GET /schema/export?format=mermaid - Export schema in various formats
- GET /schema/migrations - List all migrations

**Usage**:
Navigate to /schema-viewer.html in the admin UI to:
- Browse all tables and columns
- View relationships visually
- Generate SQLAlchemy models from existing DB
- Download ERD diagrams
- Export schema in multiple formats

**Supported Formats**:
- Mermaid (for diagrams in markdown)
- DBML (for dbdiagram.io)
- Graphviz DOT (for complex visualizations)
- JSON (for programmatic access)
- SQLAlchemy Models (Python code)
""",
                "examples": [
                    "GET /schema/inspect",
                    "GET /schema/models",
                    "GET /schema/export?format=mermaid"
                ]
            },

            # Migrations
            {
                "id": "migrations",
                "category": "migrations",
                "keywords": ["migration", "alembic", "version", "upgrade", "downgrade", "revision"],
                "title": "Database Migrations with Alembic",
                "content": """
Quantum Admin uses Alembic for database version control:

**Common Commands**:
- make migration-create MSG="description" - Create new migration
- make migration-upgrade - Apply all pending migrations
- make migration-downgrade - Rollback last migration
- make migration-history - View migration history

**Workflow**:
1. Modify SQLAlchemy models
2. Run: make migration-create MSG="add user table"
3. Review generated migration file
4. Apply: make migration-upgrade

**Auto-generation**:
Alembic can auto-detect model changes:
- New tables
- New columns
- Column type changes
- Index additions
- Constraint modifications

**Best Practices**:
- Always review auto-generated migrations
- Test migrations on dev environment first
- Never edit applied migrations
- Keep migrations small and focused
- Add meaningful migration messages
- Backup database before major migrations

**API Endpoints**:
- GET /schema/migrations - List migrations
- POST /schema/migrations/create - Create migration
- POST /schema/migrations/upgrade - Run migrations
- POST /schema/migrations/downgrade - Rollback

**Configuration**:
Migrations are configured in alembic.ini and connect via DATABASE_URL environment variable.
""",
                "examples": [
                    "make migration-create MSG='add email column'",
                    "make migration-upgrade",
                    "alembic revision --autogenerate -m 'add index'"
                ]
            },

            # SQLAlchemy Models
            {
                "id": "sqlalchemy-models",
                "category": "models",
                "keywords": ["model", "sqlalchemy", "orm", "table", "column", "relationship"],
                "title": "SQLAlchemy ORM Models",
                "content": """
Quantum Admin uses SQLAlchemy for ORM (Object-Relational Mapping):

**Basic Model Structure**:
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Column Types**:
- Integer, BigInteger, SmallInteger
- String(length), Text
- Boolean
- DateTime, Date, Time
- Float, Numeric(precision, scale)
- JSON, JSONB (PostgreSQL)
- Enum

**Relationships**:
```python
# One-to-Many
class User(Base):
    posts = relationship("Post", back_populates="author")

class Post(Base):
    author_id = Column(Integer, ForeignKey('users.id'))
    author = relationship("User", back_populates="posts")
```

**Reverse Engineering**:
Use Schema Inspector to generate models from existing database:
- Navigate to /schema-viewer.html
- Click "SQLAlchemy Models" tab
- Download or copy generated code

**Best Practices**:
- Use descriptive model names (singular)
- Add __repr__ for debugging
- Use indexes on frequently queried columns
- Define relationships explicitly
- Use Enum for fixed choices
- Add validators for data integrity
""",
                "examples": [
                    "class User(Base): __tablename__ = 'users'",
                    "username = Column(String(50), unique=True)",
                    "posts = relationship('Post', back_populates='author')"
                ]
            },

            # Container Management
            {
                "id": "container-management",
                "category": "containers",
                "keywords": ["container", "docker", "deploy", "wizard", "image", "volume"],
                "title": "Container Management",
                "content": """
Quantum Admin includes a revolutionary Container Creation Wizard:

**Features**:
- Visual container designer with drag-and-drop
- Pre-configured templates (PostgreSQL, Redis, MongoDB, Nginx, etc.)
- Real-time configuration validation
- Docker Compose generation
- One-click deployment

**API Endpoints**:
- GET /containers - List all containers
- POST /containers - Create new container
- GET /containers/{id} - Get container details
- POST /containers/{id}/start - Start container
- POST /containers/{id}/stop - Stop container
- DELETE /containers/{id} - Remove container
- GET /containers/{id}/logs - View container logs
- GET /containers/{id}/stats - Real-time statistics

**Container Wizard Features**:
1. **Template Selection**: Choose from 15+ pre-configured templates
2. **Configuration**: Set environment variables, ports, volumes
3. **Network Setup**: Configure networks and links
4. **Resource Limits**: Set CPU and memory constraints
5. **Health Checks**: Configure container health monitoring
6. **Visual Designer**: Drag-and-drop interface for complex setups

**Docker Compose Export**:
Export entire stack as docker-compose.yml for version control and deployment.

**Best Practices**:
- Use named volumes for data persistence
- Set resource limits to prevent overconsumption
- Configure health checks for critical services
- Use environment variables for configuration
- Tag images for version control
- Regular cleanup of unused containers/images
""",
                "examples": [
                    "POST /containers with template='postgres'",
                    "GET /containers/{id}/logs?tail=100",
                    "docker-compose up -d"
                ]
            },

            # Pipeline Editor
            {
                "id": "pipeline-editor",
                "category": "pipelines",
                "keywords": ["pipeline", "jenkins", "ci/cd", "jenkinsfile", "stage", "deployment"],
                "title": "Jenkins Pipeline Editor",
                "content": """
Quantum Admin features a visual Jenkins Pipeline Editor with custom XML syntax:

**Quantum Pipeline Syntax (q:pipeline)**:
```xml
<?xml version="1.0"?>
<q:pipeline name="Build and Deploy">
    <q:stage name="Build">
        <q:step>npm install</q:step>
        <q:step>npm run build</q:step>
    </q:stage>

    <q:stage name="Test">
        <q:step>npm test</q:step>
        <q:step>npm run lint</q:step>
    </q:stage>

    <q:stage name="Deploy">
        <q:step parallel="true">
            <q:task>deploy-staging</q:task>
            <q:task>deploy-production</q:task>
        </q:step>
    </q:stage>
</q:pipeline>
```

**Features**:
- Visual pipeline builder
- Syntax validation
- Jenkinsfile generation
- Template library
- Real-time preview
- Export to Jenkins

**API Endpoints**:
- POST /pipelines/parse - Parse q:pipeline XML
- POST /pipelines/generate - Generate Jenkinsfile
- GET /pipelines/templates - Get pipeline templates
- POST /pipelines/validate - Validate pipeline syntax

**Best Practices**:
- Keep stages focused and atomic
- Use descriptive stage names
- Implement proper error handling
- Add notifications for failures
- Use parallel execution when possible
- Version control Jenkinsfiles
- Test pipelines in dev environment

**Advanced Features**:
- Parallel stage execution
- Conditional stages
- Environment variables
- Credentials management
- Post-build actions
""",
                "examples": [
                    "<q:stage name='Build'><q:step>npm install</q:step></q:stage>",
                    "<q:step parallel='true'>",
                    "POST /pipelines/generate"
                ]
            },

            # Authentication
            {
                "id": "authentication",
                "category": "auth",
                "keywords": ["auth", "authentication", "login", "jwt", "token", "session", "user"],
                "title": "Authentication System",
                "content": """
Quantum Admin includes enterprise-grade authentication:

**Features**:
- JWT (JSON Web Token) based authentication
- Secure password hashing with bcrypt
- Session management
- Role-based access control (RBAC)
- Token refresh mechanism
- Multi-factor authentication ready

**API Endpoints**:
- POST /auth/register - Register new user
- POST /auth/login - Login and get JWT token
- POST /auth/refresh - Refresh access token
- POST /auth/logout - Logout user
- GET /auth/me - Get current user info
- POST /auth/change-password - Change password

**Using JWT Tokens**:
```javascript
// Login
const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
});
const { access_token } = await response.json();

// Use token in requests
fetch('/api/protected', {
    headers: { 'Authorization': `Bearer ${access_token}` }
});
```

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

**Security Features**:
- Passwords hashed with bcrypt (12 rounds)
- JWT tokens with expiration
- Secure HTTP-only cookies option
- CORS protection
- Rate limiting on auth endpoints
- Account lockout after failed attempts

**Best Practices**:
- Always use HTTPS in production
- Store tokens securely (httpOnly cookies)
- Implement token refresh
- Set appropriate token expiration
- Use strong password requirements
- Enable 2FA for admin users
- Log authentication events
- Regular security audits
""",
                "examples": [
                    "POST /auth/login with {username, password}",
                    "Authorization: Bearer <token>",
                    "POST /auth/refresh"
                ]
            },

            # WebSocket
            {
                "id": "websocket",
                "category": "websocket",
                "keywords": ["websocket", "realtime", "live", "update", "notification", "ws"],
                "title": "WebSocket Real-time Updates",
                "content": """
Quantum Admin supports WebSocket for real-time communication:

**Features**:
- Bi-directional real-time communication
- Automatic reconnection
- Event-based messaging
- Broadcast to all clients
- Room-based messaging
- Connection authentication

**Client Usage**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected');
    ws.send(JSON.stringify({ type: 'subscribe', channel: 'metrics' }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onclose = () => {
    console.log('Disconnected');
};
```

**Server Events**:
- container_status - Container state changes
- metric_update - System metrics updates
- notification - User notifications
- log_entry - New log entries
- alert - System alerts

**Event Types**:
```python
# Send to specific client
await websocket.send_json({
    "type": "notification",
    "message": "Task completed",
    "timestamp": datetime.now()
})

# Broadcast to all
await manager.broadcast({
    "type": "metric_update",
    "cpu": 45.2,
    "memory": 62.1
})
```

**Best Practices**:
- Implement reconnection logic
- Handle connection errors gracefully
- Validate all incoming messages
- Use event types for routing
- Implement heartbeat/ping
- Set connection timeouts
- Authenticate WebSocket connections
- Rate limit messages

**Use Cases**:
- Live container status updates
- Real-time metrics dashboard
- Chat/notification system
- Collaborative editing
- Log streaming
- Progress updates
""",
                "examples": [
                    "ws = new WebSocket('ws://localhost:8000/ws')",
                    "ws.send(JSON.stringify({type: 'subscribe'}))",
                    "await websocket.send_json(data)"
                ]
            },

            # Monitoring
            {
                "id": "monitoring",
                "category": "monitoring",
                "keywords": ["monitoring", "metrics", "dashboard", "stats", "cpu", "memory", "performance"],
                "title": "System Monitoring",
                "content": """
Quantum Admin provides comprehensive system monitoring:

**Metrics Collected**:
- CPU usage (per core and total)
- Memory usage (RAM and swap)
- Disk I/O and usage
- Network traffic
- Container statistics
- Database connections
- API response times
- Error rates

**API Endpoints**:
- GET /metrics - Current system metrics
- GET /metrics/history?minutes=60 - Historical metrics
- GET /metrics/containers - Container-specific metrics
- GET /metrics/database - Database performance
- GET /health - Health check endpoint

**Monitoring Dashboard Features**:
- Real-time charts (CPU, Memory, Network)
- Container status overview
- Active database connections
- API endpoint latency
- Error logs and alerts
- Custom metric widgets

**Metrics Format**:
```json
{
    "cpu": {
        "percent": 45.2,
        "per_core": [40.1, 50.3, 42.8, 48.1]
    },
    "memory": {
        "total": 16000000000,
        "used": 9920000000,
        "percent": 62.0
    },
    "disk": {
        "total": 500000000000,
        "used": 250000000000,
        "percent": 50.0
    }
}
```

**Alerting**:
- Configure thresholds for alerts
- Email/webhook notifications
- Alert history and management
- Automatic incident creation

**Best Practices**:
- Set appropriate alert thresholds
- Monitor trends, not just current values
- Regular performance reviews
- Correlate metrics with events
- Archive historical data
- Set up automated responses
- Document baseline metrics
""",
                "examples": [
                    "GET /metrics",
                    "GET /metrics/history?minutes=120",
                    "GET /health"
                ]
            },

            # API Development
            {
                "id": "api-development",
                "category": "api",
                "keywords": ["api", "rest", "endpoint", "fastapi", "swagger", "openapi"],
                "title": "API Development",
                "content": """
Quantum Admin is built on FastAPI with automatic API documentation:

**Key Features**:
- Automatic OpenAPI (Swagger) docs at /docs
- Alternative ReDoc at /redoc
- Request/response validation with Pydantic
- Dependency injection
- Async support
- CORS middleware
- Authentication middleware

**Creating Endpoints**:
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    email: str

@router.post("/users")
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Validate and create user
    return {"id": 1, "username": user.username}

# Add router to main app
app.include_router(router, prefix="/api", tags=["Users"])
```

**Response Models**:
```python
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/users/{id}", response_model=UserResponse)
async def get_user(id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

**Best Practices**:
- Use Pydantic models for validation
- Implement proper error handling
- Add response models for type safety
- Use dependency injection
- Tag endpoints for organization
- Add detailed docstrings
- Version your API
- Implement rate limiting
- Add request/response logging

**Testing APIs**:
- Use /docs for interactive testing
- Write pytest tests
- Use httpx for async tests
- Mock external dependencies
""",
                "examples": [
                    "@router.post('/users', response_model=UserResponse)",
                    "user: UserCreate = Body(...)",
                    "db: Session = Depends(get_db)"
                ]
            },

            # Frontend Development
            {
                "id": "frontend-development",
                "category": "frontend",
                "keywords": ["frontend", "ui", "javascript", "html", "css", "component"],
                "title": "Frontend Development",
                "content": """
Quantum Admin frontend is built with vanilla JavaScript and modern CSS:

**Project Structure**:
```
frontend/
├── index.html          # Main dashboard
├── styles.css          # Global styles
├── quantum-enhancements.css  # Enhanced components
├── quantum-enhancements.js   # Core functionality
├── i18n.js            # Internationalization
├── websocket-client.js       # WebSocket handler
├── schema-viewer.html/js     # Schema inspector
├── containers.html/js        # Container wizard
└── pipeline-editor.html/js   # Pipeline builder
```

**Quantum UI Components**:
- Cards with gradients
- Stat widgets
- Interactive tables
- Modal dialogs
- Toast notifications
- Loading spinners
- Progress bars
- Tabs and accordions

**CSS Features**:
- CSS Grid for layouts
- Flexbox for alignment
- CSS Variables for theming
- Smooth transitions
- Responsive design
- Dark mode ready

**JavaScript Patterns**:
```javascript
// API calls
async function loadData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        renderData(data);
    } catch (error) {
        showToast('Error loading data', 'error');
    }
}

// WebSocket integration
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateUI(data);
};
```

**Best Practices**:
- Use async/await for API calls
- Handle errors gracefully
- Show loading states
- Debounce user input
- Validate forms client-side
- Use semantic HTML
- Optimize for performance
- Make it accessible (ARIA)
- Test cross-browser
- Mobile-first design

**Quantum Enhancements**:
- Keyboard shortcuts (Ctrl+K for command palette)
- Auto-save functionality
- Drag-and-drop support
- Real-time updates via WebSocket
- Client-side caching
- Internationalization (i18n)
""",
                "examples": [
                    "await fetch('/api/endpoint')",
                    "querySelector('.quantum-card')",
                    "ws.send(JSON.stringify(data))"
                ]
            },

            # SQL Query Optimization
            {
                "id": "sql-optimization",
                "category": "database",
                "keywords": ["sql", "query", "optimize", "index", "explain", "slow query"],
                "title": "SQL Query Optimization",
                "content": """
Tips for optimizing SQL queries in Quantum Admin:

**Indexing Strategies**:
- Index columns used in WHERE clauses
- Index foreign key columns
- Composite indexes for multi-column filters
- Avoid over-indexing (slows writes)

```sql
-- Good indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);

-- Bad: too many single-column indexes
CREATE INDEX idx_users_name ON users(name);
CREATE INDEX idx_users_city ON users(city);
CREATE INDEX idx_users_state ON users(state);
-- Better: composite
CREATE INDEX idx_users_location ON users(city, state);
```

**Query Patterns**:
- Use LIMIT for large result sets
- Avoid SELECT * (specify columns)
- Use EXPLAIN to analyze queries
- Avoid N+1 queries (use joins/eager loading)
- Use EXISTS instead of COUNT for existence checks

```sql
-- Bad: N+1 problem
SELECT * FROM users;
-- Then for each user:
SELECT * FROM orders WHERE user_id = ?;

-- Good: Single query with join
SELECT u.*, o.*
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

**SQLAlchemy Optimization**:
```python
# Eager loading to avoid N+1
users = db.query(User).options(
    joinedload(User.orders),
    joinedload(User.profile)
).all()

# Select specific columns
users = db.query(User.id, User.username).all()

# Use limit
users = db.query(User).limit(100).all()
```

**Connection Pooling**:
- Reuse connections (don't create per query)
- Set appropriate pool size
- Configure pool timeout
- Monitor connection usage

**Monitoring Slow Queries**:
- Enable slow query log
- Use Quantum Admin monitoring
- Set slow query threshold
- Regular query analysis

**Best Practices**:
- Paginate large result sets
- Cache frequently accessed data
- Use database-specific features
- Regular VACUUM/ANALYZE (PostgreSQL)
- Monitor query execution time
- Profile before optimizing
""",
                "examples": [
                    "CREATE INDEX idx_email ON users(email);",
                    "SELECT id, name FROM users LIMIT 100;",
                    "EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';"
                ]
            },

            # Deployment
            {
                "id": "deployment",
                "category": "deployment",
                "keywords": ["deploy", "production", "docker", "install", "setup", "configuration"],
                "title": "Deployment Guide",
                "content": """
Deploying Quantum Admin to production:

**Installation Methods**:

1. **Quick Install (Linux/macOS)**:
```bash
curl -fsSL https://raw.githubusercontent.com/quantum/quantum-admin/main/install.sh | bash
```

2. **Quick Install (Windows)**:
```powershell
irm https://raw.githubusercontent.com/quantum/quantum-admin/main/setup.ps1 | iex
```

3. **Docker Deployment**:
```bash
docker-compose up -d
```

4. **Manual Installation**:
```bash
python install.py
```

**Environment Configuration**:
```bash
# .env file
DATABASE_URL=postgresql://user:pass@localhost/quantum
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key-here
OLLAMA_URL=http://localhost:11434
AI_ENABLED=true
CORS_ORIGINS=["http://localhost:3000"]
```

**Production Checklist**:
- [ ] Set strong SECRET_KEY
- [ ] Configure DATABASE_URL
- [ ] Enable HTTPS/SSL
- [ ] Set up reverse proxy (Nginx)
- [ ] Configure firewall rules
- [ ] Enable backup automation
- [ ] Set up monitoring/alerts
- [ ] Configure log rotation
- [ ] Set resource limits
- [ ] Enable rate limiting
- [ ] Review security settings
- [ ] Test disaster recovery

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name quantum.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Systemd Service** (Linux):
```ini
[Unit]
Description=Quantum Admin
After=network.target

[Service]
User=quantum
WorkingDirectory=/opt/quantum-admin
ExecStart=/opt/quantum-admin/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Monitoring in Production**:
- Use /health endpoint for uptime checks
- Monitor /metrics for performance
- Set up log aggregation
- Configure alerts
- Regular security audits

**Scaling**:
- Horizontal: Run multiple instances behind load balancer
- Vertical: Increase server resources
- Database: Use read replicas
- Caching: Redis for session/query cache
- CDN: Static assets
""",
                "examples": [
                    "bash install.sh --quick",
                    "docker-compose up -d",
                    "systemctl start quantum-admin"
                ]
            },

            # Troubleshooting
            {
                "id": "troubleshooting",
                "category": "troubleshooting",
                "keywords": ["error", "problem", "issue", "debug", "fix", "not working", "troubleshoot"],
                "title": "Troubleshooting Guide",
                "content": """
Common issues and solutions for Quantum Admin:

**Connection Errors**:

Problem: Cannot connect to database
Solution:
- Check DATABASE_URL in .env
- Verify database server is running
- Check firewall rules
- Test connection: `psql <DATABASE_URL>`

Problem: Redis connection failed
Solution:
- Verify Redis is running: `redis-cli ping`
- Check REDIS_URL in .env
- Check Redis authentication

**Installation Issues**:

Problem: Python dependencies fail to install
Solution:
```bash
# Update pip
pip install --upgrade pip setuptools wheel

# Install with verbose output
pip install -r requirements.txt -v

# Use specific Python version
python3.11 -m pip install -r requirements.txt
```

Problem: Permission denied during installation
Solution:
- Run with appropriate permissions
- Use virtual environment
- Check file ownership

**Runtime Errors**:

Problem: 500 Internal Server Error
Solution:
- Check application logs
- Enable debug mode (dev only): DEBUG=true
- Verify all environment variables
- Check database migrations are applied

Problem: WebSocket connection fails
Solution:
- Verify WebSocket endpoint: ws://host:port/ws
- Check CORS configuration
- Ensure proxy supports WebSocket
- Check firewall allows WebSocket

**Performance Issues**:

Problem: Slow queries
Solution:
- Check query execution with EXPLAIN
- Add appropriate indexes
- Review connection pool settings
- Enable query caching

Problem: High memory usage
Solution:
- Check for memory leaks in custom code
- Review connection pool size
- Monitor long-running queries
- Adjust worker count

**Container Issues**:

Problem: Container fails to start
Solution:
- Check Docker daemon: `docker ps`
- Review container logs: `docker logs <container>`
- Verify port availability
- Check resource limits

Problem: Container networking issues
Solution:
- Verify network exists: `docker network ls`
- Check port mappings
- Review firewall rules
- Test connectivity from host

**AI/SLM Issues**:

Problem: Ollama not responding
Solution:
- Check Ollama is running: `ollama list`
- Verify OLLAMA_URL in .env
- Check model is downloaded: `ollama pull phi3`
- Review Ollama logs

Problem: AI gives poor responses
Solution:
- Check RAG knowledge base is loaded
- Verify schema inspector has access to DB
- Review conversation context
- Adjust AI temperature/tokens

**Getting Help**:
- Check logs in quantum_admin/logs/
- Review API docs at /docs
- Enable verbose logging
- Check GitHub issues
- Join community Discord
""",
                "examples": [
                    "docker logs quantum-admin",
                    "tail -f logs/quantum-admin.log",
                    "pytest tests/ -v"
                ]
            }
        ]

    def _load_intent_patterns(self) -> List[Dict[str, Any]]:
        """Load intent recognition patterns"""
        return [
            {
                "intent": "databinding",
                "patterns": [
                    r"\{.*\}",
                    r"variable",
                    r"bind(ing)?",
                    r"expression",
                    r"context"
                ]
            },
            {
                "intent": "component",
                "patterns": [
                    r"component",
                    r"create.*component",
                    r"structure",
                    r"template"
                ]
            },
            {
                "intent": "loop",
                "patterns": [
                    r"loop",
                    r"iterate",
                    r"array",
                    r"for.*each"
                ]
            },
            {
                "intent": "conditional",
                "patterns": [
                    r"\bif\b",
                    r"condition",
                    r"else"
                ]
            },
            {
                "intent": "database",
                "patterns": [
                    r"database",
                    r"query",
                    r"sql",
                    r"select",
                    r"insert",
                    r"update",
                    r"delete",
                    r"optimi[zs]e.*query"
                ]
            },
            {
                "intent": "error",
                "patterns": [
                    r"error",
                    r"bug",
                    r"issue",
                    r"problem",
                    r"not working",
                    r"fail(ed|ing)?"
                ]
            },
            {
                "intent": "security",
                "patterns": [
                    r"security",
                    r"auth(entication)?",
                    r"xss",
                    r"injection",
                    r"csrf"
                ]
            },
            {
                "intent": "performance",
                "patterns": [
                    r"performance",
                    r"slow",
                    r"optimi[zs]e",
                    r"fast(er)?",
                    r"cache"
                ]
            },
            {
                "intent": "schema",
                "patterns": [
                    r"schema",
                    r"erd",
                    r"diagram",
                    r"table.*structure",
                    r"inspect.*database",
                    r"view.*schema",
                    r"database.*structure"
                ]
            },
            {
                "intent": "migrations",
                "patterns": [
                    r"migration",
                    r"alembic",
                    r"version",
                    r"upgrade",
                    r"downgrade",
                    r"revision"
                ]
            },
            {
                "intent": "models",
                "patterns": [
                    r"model",
                    r"sqlalchemy",
                    r"orm",
                    r"generate.*model",
                    r"create.*model",
                    r"relationship"
                ]
            },
            {
                "intent": "containers",
                "patterns": [
                    r"container",
                    r"docker",
                    r"deploy",
                    r"wizard",
                    r"image",
                    r"volume"
                ]
            },
            {
                "intent": "pipelines",
                "patterns": [
                    r"pipeline",
                    r"jenkins",
                    r"ci/cd",
                    r"jenkinsfile",
                    r"stage",
                    r"deployment"
                ]
            },
            {
                "intent": "auth",
                "patterns": [
                    r"auth",
                    r"login",
                    r"jwt",
                    r"token",
                    r"session",
                    r"user",
                    r"password"
                ]
            },
            {
                "intent": "websocket",
                "patterns": [
                    r"websocket",
                    r"realtime",
                    r"live.*update",
                    r"\bws\b",
                    r"notification"
                ]
            },
            {
                "intent": "monitoring",
                "patterns": [
                    r"monitor(ing)?",
                    r"metrics",
                    r"dashboard",
                    r"stats",
                    r"cpu",
                    r"memory"
                ]
            },
            {
                "intent": "api",
                "patterns": [
                    r"api",
                    r"rest",
                    r"endpoint",
                    r"fastapi",
                    r"swagger",
                    r"openapi"
                ]
            },
            {
                "intent": "frontend",
                "patterns": [
                    r"frontend",
                    r"ui",
                    r"javascript",
                    r"html",
                    r"css",
                    r"component"
                ]
            },
            {
                "intent": "deployment",
                "patterns": [
                    r"deploy",
                    r"production",
                    r"install",
                    r"setup",
                    r"configuration"
                ]
            },
            {
                "intent": "troubleshooting",
                "patterns": [
                    r"troubleshoot",
                    r"debug",
                    r"fix",
                    r"resolve",
                    r"diagnose"
                ]
            }
        ]

    def detect_intent(self, query: str) -> List[str]:
        """Detect intents from query"""
        query_lower = query.lower()
        detected = []

        for intent_def in self.intent_patterns:
            intent = intent_def["intent"]
            patterns = intent_def["patterns"]

            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected.append(intent)
                    break

        return detected

    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant documents
        Returns top N most relevant documents
        """
        query_lower = query.lower()
        results = []

        # Detect intents
        intents = self.detect_intent(query)

        # Score each document
        for doc in self.knowledge_base:
            score = 0

            # Category match
            if doc["category"] in intents:
                score += 10

            # Keyword matches
            for keyword in doc["keywords"]:
                if keyword in query_lower:
                    score += 5

            # Title match
            if any(word in doc["title"].lower() for word in query_lower.split()):
                score += 3

            # Content match (partial)
            query_words = query_lower.split()
            content_lower = doc["content"].lower()
            for word in query_words:
                if len(word) > 3 and word in content_lower:
                    score += 1

            if score > 0:
                results.append((score, doc))

        # Sort by score and return top N
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in results[:limit]]

    def get_context(self, query: str) -> str:
        """
        Get context for AI response
        Returns formatted context from relevant documents
        """
        relevant_docs = self.search(query)

        if not relevant_docs:
            return ""

        context = "**Relevant Documentation:**\n\n"

        for doc in relevant_docs:
            context += f"## {doc['title']}\n\n"
            context += doc['content'].strip() + "\n\n"

            if doc.get('examples'):
                context += "**Examples:**\n"
                for example in doc['examples']:
                    context += f"- `{example}`\n"
                context += "\n"

        return context

    def enhance_response(self, query: str, base_response: str) -> str:
        """
        Enhance AI response with RAG context
        """
        context = self.get_context(query)

        if not context:
            return base_response

        # Combine context with response
        enhanced = context + "\n\n" + base_response

        return enhanced


# Singleton instance
_rag_instance = None


def get_rag_system() -> QuantumRAG:
    """Get or create RAG system instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = QuantumRAG()
    return _rag_instance
