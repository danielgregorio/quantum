# Quantum Resource Manager + Test Suite - Plano Completo

## Visao Geral

Sistema enterprise-grade com:
- **Resource Manager**: Gerenciamento centralizado de portas, secrets, configs
- **Component Discovery**: Scan automatico de projetos Quantum
- **Test Suite Generator**: Criacao automatica de testes baseado em componentes
- **Test Runner**: Execucao distribuida nos ambientes com CI/CD integration

---

## Parte 1: Resource Manager

### 1.1 Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESOURCE MANAGER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PortManager  │  │SecretManager │  │ConfigManager │          │
│  │              │  │              │  │              │          │
│  │ - allocate() │  │ - encrypt()  │  │ - templates  │          │
│  │ - release()  │  │ - decrypt()  │  │ - generate() │          │
│  │ - reserve()  │  │ - rotate()   │  │ - validate() │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └────────────────┼─────────────────┘                   │
│                          ▼                                      │
│              ┌──────────────────────┐                          │
│              │   ResourceRegistry   │                          │
│              │   (SQLite + Cache)   │                          │
│              └──────────────────────┘                          │
│                          │                                      │
│         ┌────────────────┼────────────────┐                    │
│         ▼                ▼                ▼                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │  Project   │  │Environment │  │  Service   │               │
│  │ Resources  │  │ Resources  │  │ Discovery  │               │
│  └────────────┘  └────────────┘  └────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Modelos de Dados

```python
# quantum_admin/backend/models.py

class PortAllocation(Base):
    """Track all port allocations across hosts"""
    __tablename__ = 'port_allocations'

    id = Column(Integer, primary_key=True)

    # What owns this port
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True)
    service_name = Column(String(100), nullable=False)  # quantumblog-prod, blog-db

    # Port info
    port = Column(Integer, nullable=False)
    port_type = Column(String(50))  # app, database, cache, web, custom
    host = Column(String(255), default='localhost')  # localhost, forge, 10.10.1.40

    # Status
    status = Column(String(50), default='allocated')  # allocated, reserved, released
    is_reserved = Column(Boolean, default=False)  # Reserved ports can't be auto-allocated
    reserved_reason = Column(String(255))  # "production-only", "legacy-app"

    # Metadata
    allocated_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50))  # healthy, unhealthy, unknown

    # Unique constraint: one port per host
    __table_args__ = (
        UniqueConstraint('port', 'host', name='uq_port_host'),
    )


class PortRange(Base):
    """Define port ranges for different service types"""
    __tablename__ = 'port_ranges'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)  # apps, databases, cache, web
    start_port = Column(Integer, nullable=False)
    end_port = Column(Integer, nullable=False)
    host = Column(String(255), default='*')  # * = all hosts, or specific host
    description = Column(String(255))

    # Default ranges
    # apps: 8000-8999
    # databases: 5400-5499
    # cache: 6370-6399
    # web: 3000-3099


class Secret(Base):
    """Encrypted secrets storage"""
    __tablename__ = 'secrets'

    id = Column(Integer, primary_key=True)

    # Scope
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True)
    scope = Column(String(50), default='project')  # global, project, environment

    # Secret data
    key = Column(String(255), nullable=False)
    encrypted_value = Column(Text, nullable=False)

    # Metadata
    description = Column(String(500))
    is_sensitive = Column(Boolean, default=True)  # Hide in UI
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_rotated = Column(DateTime)

    # Unique per scope
    __table_args__ = (
        UniqueConstraint('key', 'project_id', 'environment_id', name='uq_secret_scope'),
    )


class ServiceRegistry(Base):
    """Service discovery registry"""
    __tablename__ = 'service_registry'

    id = Column(Integer, primary_key=True)

    # Service identity
    name = Column(String(100), nullable=False)
    service_type = Column(String(50))  # app, database, cache, queue, gateway

    # Location
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), default='http')  # http, https, tcp, grpc

    # Health
    health_endpoint = Column(String(255))  # /health, /api/health
    health_interval = Column(Integer, default=30)  # seconds
    last_health_check = Column(DateTime)
    health_status = Column(String(50), default='unknown')
    consecutive_failures = Column(Integer, default=0)

    # Metadata
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True)
    metadata_json = Column(Text)  # {"version": "1.0", "tags": ["api", "v2"]}

    registered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 1.3 Resource Manager Service

```python
# quantum_admin/backend/resource_manager.py (~500 linhas)

class ResourceManager:
    """Centralized resource management service"""

    def __init__(self, db: Session):
        self.db = db
        self.port_manager = PortManager(db)
        self.secret_manager = SecretManager(db)
        self.service_registry = ServiceRegistryManager(db)
        self.config_generator = ConfigGenerator(db)

    # =========================================================================
    # Port Management
    # =========================================================================

    def allocate_port(
        self,
        service_name: str,
        port_type: str = "app",
        host: str = "localhost",
        project_id: int = None,
        environment_id: int = None,
        preferred_port: int = None
    ) -> int:
        """
        Allocate an available port for a service.

        Args:
            service_name: Unique service identifier
            port_type: Type of service (app, database, cache, web)
            host: Target host
            project_id: Optional project association
            environment_id: Optional environment association
            preferred_port: Try this port first if available

        Returns:
            Allocated port number

        Raises:
            ResourceExhaustedError: No ports available in range
        """
        return self.port_manager.allocate(
            service_name, port_type, host,
            project_id, environment_id, preferred_port
        )

    def release_port(self, service_name: str, host: str = "localhost") -> bool:
        """Release a port allocation"""
        return self.port_manager.release(service_name, host)

    def reserve_port(
        self,
        port: int,
        host: str,
        reason: str,
        service_name: str = None
    ) -> bool:
        """Reserve a specific port (prevents auto-allocation)"""
        return self.port_manager.reserve(port, host, reason, service_name)

    def get_port(self, service_name: str, host: str = "localhost") -> Optional[int]:
        """Get allocated port for a service"""
        return self.port_manager.get(service_name, host)

    def list_allocations(
        self,
        host: str = None,
        project_id: int = None,
        include_released: bool = False
    ) -> List[PortAllocation]:
        """List all port allocations with optional filters"""
        return self.port_manager.list(host, project_id, include_released)

    def check_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if a port is available"""
        return self.port_manager.is_available(port, host)

    def get_port_ranges(self) -> List[PortRange]:
        """Get configured port ranges"""
        return self.port_manager.get_ranges()

    def set_port_range(
        self,
        name: str,
        start: int,
        end: int,
        host: str = "*"
    ) -> PortRange:
        """Configure a port range"""
        return self.port_manager.set_range(name, start, end, host)

    # =========================================================================
    # Secret Management
    # =========================================================================

    def set_secret(
        self,
        key: str,
        value: str,
        scope: str = "global",
        project_id: int = None,
        environment_id: int = None,
        description: str = None
    ) -> Secret:
        """Store an encrypted secret"""
        return self.secret_manager.set(
            key, value, scope, project_id, environment_id, description
        )

    def get_secret(
        self,
        key: str,
        project_id: int = None,
        environment_id: int = None
    ) -> Optional[str]:
        """Retrieve and decrypt a secret"""
        return self.secret_manager.get(key, project_id, environment_id)

    def list_secrets(
        self,
        project_id: int = None,
        environment_id: int = None,
        include_values: bool = False
    ) -> List[Dict]:
        """List secrets (optionally with decrypted values)"""
        return self.secret_manager.list(project_id, environment_id, include_values)

    def delete_secret(self, key: str, project_id: int = None) -> bool:
        """Delete a secret"""
        return self.secret_manager.delete(key, project_id)

    def rotate_secret(self, key: str, new_value: str, project_id: int = None) -> bool:
        """Rotate a secret value"""
        return self.secret_manager.rotate(key, new_value, project_id)

    # =========================================================================
    # Service Discovery
    # =========================================================================

    def register_service(
        self,
        name: str,
        host: str,
        port: int,
        service_type: str = "app",
        health_endpoint: str = "/health",
        project_id: int = None,
        environment_id: int = None,
        metadata: Dict = None
    ) -> ServiceRegistry:
        """Register a service for discovery"""
        return self.service_registry.register(
            name, host, port, service_type, health_endpoint,
            project_id, environment_id, metadata
        )

    def discover(self, name: str, healthy_only: bool = True) -> Optional[ServiceRegistry]:
        """Discover a service by name"""
        return self.service_registry.discover(name, healthy_only)

    def discover_by_type(
        self,
        service_type: str,
        project_id: int = None
    ) -> List[ServiceRegistry]:
        """Discover all services of a type"""
        return self.service_registry.discover_by_type(service_type, project_id)

    def health_check_all(self) -> Dict[str, Dict]:
        """Run health checks on all registered services"""
        return self.service_registry.health_check_all()

    def deregister_service(self, name: str) -> bool:
        """Remove a service from registry"""
        return self.service_registry.deregister(name)

    # =========================================================================
    # Config Generation
    # =========================================================================

    def generate_env_file(
        self,
        project_id: int,
        environment_id: int = None
    ) -> str:
        """Generate complete .env file with all configs and secrets"""
        return self.config_generator.env_file(project_id, environment_id)

    def generate_docker_compose(
        self,
        project_id: int,
        environment_id: int = None
    ) -> str:
        """Generate docker-compose.yml with correct ports and networks"""
        return self.config_generator.docker_compose(project_id, environment_id)

    def generate_nginx_conf(
        self,
        project_id: int,
        include_ssl: bool = True
    ) -> str:
        """Generate nginx configuration with upstreams"""
        return self.config_generator.nginx_conf(project_id, include_ssl)

    def generate_quantum_config(self, project_id: int) -> str:
        """Generate quantum.config.yaml with all datasources and settings"""
        return self.config_generator.quantum_config(project_id)
```

### 1.4 Port Manager Implementation

```python
# quantum_admin/backend/port_manager.py (~200 linhas)

class PortManager:
    """Manages port allocation and tracking"""

    DEFAULT_RANGES = {
        "app": (8000, 8999),
        "database": (5400, 5499),
        "cache": (6370, 6399),
        "web": (3000, 3099),
        "queue": (5670, 5699),
    }

    def __init__(self, db: Session):
        self.db = db
        self._ensure_default_ranges()

    def allocate(
        self,
        service_name: str,
        port_type: str,
        host: str,
        project_id: int = None,
        environment_id: int = None,
        preferred_port: int = None
    ) -> int:
        # Check if already allocated
        existing = self.get(service_name, host)
        if existing:
            return existing

        # Try preferred port first
        if preferred_port and self.is_available(preferred_port, host):
            return self._do_allocate(
                service_name, preferred_port, port_type, host,
                project_id, environment_id
            )

        # Find next available in range
        range_obj = self._get_range(port_type, host)
        for port in range(range_obj.start_port, range_obj.end_port + 1):
            if self.is_available(port, host):
                return self._do_allocate(
                    service_name, port, port_type, host,
                    project_id, environment_id
                )

        raise ResourceExhaustedError(
            f"No available ports in {port_type} range for host {host}"
        )

    def is_available(self, port: int, host: str) -> bool:
        """Check if port is available (not allocated and not in use)"""
        # Check database
        allocation = self.db.query(PortAllocation).filter(
            PortAllocation.port == port,
            PortAllocation.host == host,
            PortAllocation.status != 'released'
        ).first()

        if allocation:
            return False

        # Optionally check if port is actually in use on host
        # (for localhost, can use socket; for remote, skip or SSH check)
        if host == 'localhost':
            return self._check_port_free_local(port)

        return True

    def _check_port_free_local(self, port: int) -> bool:
        """Check if local port is free using socket"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False
```

### 1.5 API Endpoints

```python
# Adicionar em main.py

# ============================================================================
# RESOURCE MANAGER ENDPOINTS
# ============================================================================

@app.get("/resources/ports", tags=["Resource Manager"])
def list_port_allocations(
    host: str = None,
    project_id: int = None,
    db: Session = Depends(get_db)
):
    """List all port allocations"""
    manager = ResourceManager(db)
    return manager.list_allocations(host=host, project_id=project_id)

@app.post("/resources/ports/allocate", tags=["Resource Manager"])
def allocate_port(
    service_name: str,
    port_type: str = "app",
    host: str = "localhost",
    project_id: int = None,
    preferred_port: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Allocate a port for a service"""
    manager = ResourceManager(db)
    port = manager.allocate_port(
        service_name, port_type, host, project_id,
        preferred_port=preferred_port
    )
    return {"success": True, "port": port, "service": service_name, "host": host}

@app.post("/resources/ports/release", tags=["Resource Manager"])
def release_port(
    service_name: str,
    host: str = "localhost",
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Release a port allocation"""
    manager = ResourceManager(db)
    success = manager.release_port(service_name, host)
    return {"success": success}

@app.get("/resources/ports/check/{port}", tags=["Resource Manager"])
def check_port(
    port: int,
    host: str = "localhost",
    db: Session = Depends(get_db)
):
    """Check if a port is available"""
    manager = ResourceManager(db)
    available = manager.check_port_available(port, host)
    return {"port": port, "host": host, "available": available}

@app.get("/resources/ports/ranges", tags=["Resource Manager"])
def get_port_ranges(db: Session = Depends(get_db)):
    """Get configured port ranges"""
    manager = ResourceManager(db)
    return manager.get_port_ranges()

@app.get("/resources/secrets", tags=["Resource Manager"])
def list_secrets(
    project_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """List secrets (without values)"""
    manager = ResourceManager(db)
    return manager.list_secrets(project_id=project_id, include_values=False)

@app.post("/resources/secrets", tags=["Resource Manager"])
def create_secret(
    key: str,
    value: str,
    project_id: int = None,
    environment_id: int = None,
    description: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Create or update a secret"""
    manager = ResourceManager(db)
    scope = "global" if not project_id else ("environment" if environment_id else "project")
    secret = manager.set_secret(key, value, scope, project_id, environment_id, description)
    return {"success": True, "key": key, "scope": scope}

@app.get("/resources/services", tags=["Resource Manager"])
def list_services(
    service_type: str = None,
    project_id: int = None,
    db: Session = Depends(get_db)
):
    """List registered services"""
    manager = ResourceManager(db)
    if service_type:
        return manager.discover_by_type(service_type, project_id)
    return manager.service_registry.list_all()

@app.post("/resources/services/health-check", tags=["Resource Manager"])
def run_health_checks(
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Run health checks on all services"""
    manager = ResourceManager(db)
    return manager.health_check_all()

@app.get("/resources/generate/env/{project_id}", tags=["Resource Manager"])
def generate_env_file(
    project_id: int,
    environment_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Generate .env file content"""
    manager = ResourceManager(db)
    content = manager.generate_env_file(project_id, environment_id)
    return {"content": content, "filename": f".env.{environment_id or 'default'}"}

@app.get("/resources/generate/docker-compose/{project_id}", tags=["Resource Manager"])
def generate_docker_compose(
    project_id: int,
    environment_id: int = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Generate docker-compose.yml content"""
    manager = ResourceManager(db)
    content = manager.generate_docker_compose(project_id, environment_id)
    return {"content": content, "filename": "docker-compose.yml"}
```

### 1.6 UI Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  Resource Manager                                    [Refresh]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Port Allocations ───────────────────────────────────────┐│
│  │                                                             ││
│  │  Host: [All Hosts ▼]  Type: [All Types ▼]  [+ Reserve Port]││
│  │                                                             ││
│  │  ┌────────────────────────────────────────────────────────┐││
│  │  │ Service              Port   Type      Host      Status │││
│  │  ├────────────────────────────────────────────────────────┤││
│  │  │ quantumblog-prod     8080   app       forge     ● Used │││
│  │  │ quantumblog-staging  8082   app       forge     ● Used │││
│  │  │ quantumblog-dev      8081   app       forge     ○ Free │││
│  │  │ blog-db              5432   database  forge     ● Used │││
│  │  │ quantum-admin        8001   app       localhost ● Used │││
│  │  │ [reserved]           80     web       forge     ⊘ Rsvd │││
│  │  └────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─── Port Ranges ────────────────────────────────────────────┐│
│  │                                                             ││
│  │  [app]      8000-8999   ████████░░ 82% available           ││
│  │  [database] 5400-5499   █████████░ 99% available           ││
│  │  [cache]    6370-6399   ██████████ 100% available          ││
│  │  [web]      3000-3099   █████████░ 99% available           ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─── Service Health ─────────────────────────────────────────┐│
│  │                                                             ││
│  │  ● quantumblog-prod    http://10.10.1.40:8080/health  120ms││
│  │  ● quantumblog-staging http://10.10.1.40:8082/health   95ms││
│  │  ○ quantumblog-dev     http://10.10.1.40:8081/health  [N/A]││
│  │  ● blog-db             tcp://10.10.1.40:5432          45ms ││
│  │                                                             ││
│  │  Last check: 30s ago                    [Run Health Check] ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Parte 2: Component Discovery & Test Suite

### 2.1 Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEST SUITE SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │  Component   │────▶│    Test      │────▶│    Test      │   │
│  │  Discovery   │     │  Generator   │     │   Runner     │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                    │                    │            │
│         ▼                    ▼                    ▼            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │  - Scan .q   │     │  - Smoke     │     │  - Local     │   │
│  │  - Parse AST │     │  - API       │     │  - Docker    │   │
│  │  - Extract   │     │  - Data      │     │  - Remote    │   │
│  │    actions   │     │  - Auth      │     │  - Parallel  │   │
│  │    queries   │     │  - Edge      │     │              │   │
│  │    forms     │     │              │     │              │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│                                                                 │
│                    ┌──────────────────────┐                    │
│                    │   Results Dashboard  │                    │
│                    │   - Coverage         │                    │
│                    │   - History          │                    │
│                    │   - Comparisons      │                    │
│                    └──────────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Modelos de Dados

```python
# quantum_admin/backend/models.py

class ComponentInfo(Base):
    """Discovered component information"""
    __tablename__ = 'component_info'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    # Component identity
    file_path = Column(String(500), nullable=False)  # /components/login.q
    component_name = Column(String(100))  # LoginComponent
    component_type = Column(String(50))  # page, layout, partial, api

    # Extracted info (JSON)
    actions_json = Column(Text)  # [{"name": "login", "method": "POST", "params": [...]}]
    queries_json = Column(Text)  # [{"name": "getUser", "datasource": "main-db", "sql": "..."}]
    forms_json = Column(Text)    # [{"id": "login-form", "fields": [...], "action": "login"}]
    conditionals_json = Column(Text)  # [{"expression": "session.isLoggedIn", "branches": 2}]
    includes_json = Column(Text)  # ["/components/header.q", "/components/footer.q"]

    # Stats
    line_count = Column(Integer)
    complexity_score = Column(Integer)  # Based on conditions, loops, actions

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow)
    file_modified_at = Column(DateTime)

    # Relationships
    project = relationship("Project", backref="components")


class TestSuite(Base):
    """Test suite definition"""
    __tablename__ = 'test_suites'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Configuration
    test_type = Column(String(50))  # smoke, api, e2e, load, security
    config_json = Column(Text)  # {"timeout": 30, "retries": 3, "parallel": true}

    # Status
    is_active = Column(Boolean, default=True)
    auto_run = Column(Boolean, default=False)  # Run on deploy

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="test_suites")
    test_cases = relationship("TestCase", back_populates="suite")


class TestCase(Base):
    """Individual test case"""
    __tablename__ = 'test_cases'

    id = Column(Integer, primary_key=True)
    suite_id = Column(Integer, ForeignKey('test_suites.id'), nullable=False)
    component_id = Column(Integer, ForeignKey('component_info.id'), nullable=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Test definition
    test_type = Column(String(50))  # smoke, api, form, query, auth
    target = Column(String(255))  # URL, action name, or component path
    method = Column(String(20), default='GET')  # HTTP method for API tests

    # Input/Output
    input_json = Column(Text)  # Request body, form data, headers
    expected_json = Column(Text)  # Expected response, status, content

    # Assertions
    assertions_json = Column(Text)  # [{"type": "status", "value": 200}, {"type": "contains", "value": "Success"}]

    # Configuration
    timeout = Column(Integer, default=30)
    retries = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    # Generation info
    auto_generated = Column(Boolean, default=False)
    generation_source = Column(String(100))  # "action:login", "query:getUser"

    # Relationships
    suite = relationship("TestSuite", back_populates="test_cases")
    component = relationship("ComponentInfo")


class TestRun(Base):
    """Test execution run"""
    __tablename__ = 'test_runs'

    id = Column(Integer, primary_key=True)
    suite_id = Column(Integer, ForeignKey('test_suites.id'), nullable=False)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True)

    # Run info
    status = Column(String(50), default='pending')  # pending, running, passed, failed, error
    triggered_by = Column(String(100))  # user:admin, webhook:github, schedule:daily

    # Results
    total_tests = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Output
    logs_json = Column(Text)
    artifacts_json = Column(Text)  # Screenshots, responses, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    suite = relationship("TestSuite")
    environment = relationship("Environment")
    results = relationship("TestResult", back_populates="run")


class TestResult(Base):
    """Individual test result"""
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('test_runs.id'), nullable=False)
    test_case_id = Column(Integer, ForeignKey('test_cases.id'), nullable=False)

    # Result
    status = Column(String(50))  # passed, failed, skipped, error

    # Timing
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    duration_ms = Column(Integer)

    # Output
    response_json = Column(Text)  # Actual response
    error_message = Column(Text)
    assertion_results_json = Column(Text)  # [{"assertion": "status=200", "passed": true}]

    # Artifacts
    screenshot_path = Column(String(500))

    # Relationships
    run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCase")
```

### 2.3 Component Discovery Service

```python
# quantum_admin/backend/component_discovery.py (~300 linhas)

class ComponentDiscoveryService:
    """Scans and analyzes Quantum project components"""

    def __init__(self, db: Session):
        self.db = db

    def scan_project(self, project_id: int, project_path: str) -> List[ComponentInfo]:
        """
        Scan a project directory and discover all .q components.

        Returns:
            List of discovered ComponentInfo objects
        """
        components = []

        # Find all .q files
        q_files = self._find_q_files(project_path)

        for file_path in q_files:
            try:
                component = self._analyze_component(project_id, project_path, file_path)
                components.append(component)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")

        # Save to database
        self._save_components(project_id, components)

        return components

    def _find_q_files(self, project_path: str) -> List[str]:
        """Find all .q files in project"""
        from pathlib import Path
        return list(Path(project_path).rglob("*.q"))

    def _analyze_component(
        self,
        project_id: int,
        project_path: str,
        file_path: str
    ) -> ComponentInfo:
        """Parse and analyze a single .q file"""
        import xml.etree.ElementTree as ET

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse XML
        root = ET.fromstring(f"<root>{content}</root>")

        # Extract component info
        component_name = self._extract_component_name(root, file_path)
        component_type = self._determine_component_type(root, file_path)

        # Extract actions
        actions = self._extract_actions(root)

        # Extract queries
        queries = self._extract_queries(root)

        # Extract forms
        forms = self._extract_forms(root)

        # Extract conditionals
        conditionals = self._extract_conditionals(root)

        # Extract includes
        includes = self._extract_includes(root)

        # Calculate complexity
        complexity = self._calculate_complexity(
            len(actions), len(queries), len(conditionals)
        )

        relative_path = str(file_path).replace(project_path, '').lstrip('/\\')

        return ComponentInfo(
            project_id=project_id,
            file_path=relative_path,
            component_name=component_name,
            component_type=component_type,
            actions_json=json.dumps(actions),
            queries_json=json.dumps(queries),
            forms_json=json.dumps(forms),
            conditionals_json=json.dumps(conditionals),
            includes_json=json.dumps(includes),
            line_count=len(content.splitlines()),
            complexity_score=complexity,
            file_modified_at=datetime.fromtimestamp(os.path.getmtime(file_path))
        )

    def _extract_actions(self, root: ET.Element) -> List[Dict]:
        """Extract q:action definitions"""
        actions = []
        for action in root.findall(".//q:action", {"q": "quantum"}):
            actions.append({
                "name": action.get("name"),
                "method": action.get("method", "POST"),
                "params": self._extract_action_params(action)
            })
        return actions

    def _extract_queries(self, root: ET.Element) -> List[Dict]:
        """Extract q:query definitions"""
        queries = []
        for query in root.findall(".//q:query", {"q": "quantum"}):
            queries.append({
                "name": query.get("name"),
                "datasource": query.get("datasource"),
                "sql": query.text.strip() if query.text else ""
            })
        return queries

    def _extract_forms(self, root: ET.Element) -> List[Dict]:
        """Extract form definitions"""
        forms = []
        for form in root.findall(".//form"):
            fields = []
            for input_el in form.findall(".//input"):
                fields.append({
                    "name": input_el.get("name"),
                    "type": input_el.get("type", "text"),
                    "required": input_el.get("required") == "true"
                })
            forms.append({
                "id": form.get("id"),
                "action": form.get("q:action"),
                "fields": fields
            })
        return forms

    def get_project_components(self, project_id: int) -> List[ComponentInfo]:
        """Get all discovered components for a project"""
        return self.db.query(ComponentInfo).filter(
            ComponentInfo.project_id == project_id
        ).all()

    def get_component_stats(self, project_id: int) -> Dict:
        """Get statistics about project components"""
        components = self.get_project_components(project_id)

        total_actions = 0
        total_queries = 0
        total_forms = 0

        for c in components:
            total_actions += len(json.loads(c.actions_json or "[]"))
            total_queries += len(json.loads(c.queries_json or "[]"))
            total_forms += len(json.loads(c.forms_json or "[]"))

        return {
            "total_components": len(components),
            "total_actions": total_actions,
            "total_queries": total_queries,
            "total_forms": total_forms,
            "total_lines": sum(c.line_count for c in components),
            "avg_complexity": sum(c.complexity_score for c in components) / len(components) if components else 0
        }
```

### 2.4 Test Generator Service

```python
# quantum_admin/backend/test_generator.py (~400 linhas)

class TestGeneratorService:
    """Generates tests from discovered components"""

    def __init__(self, db: Session):
        self.db = db
        self.discovery = ComponentDiscoveryService(db)

    def generate_suite(
        self,
        project_id: int,
        suite_name: str,
        test_types: List[str] = None
    ) -> TestSuite:
        """
        Generate a complete test suite from project components.

        Args:
            project_id: Project ID
            suite_name: Name for the test suite
            test_types: Types of tests to generate (smoke, api, form, query, auth)
        """
        if not test_types:
            test_types = ["smoke", "api", "form", "query"]

        # Create suite
        suite = TestSuite(
            project_id=project_id,
            name=suite_name,
            description=f"Auto-generated test suite for project {project_id}",
            test_type="mixed",
            is_active=True
        )
        self.db.add(suite)
        self.db.flush()

        # Get components
        components = self.discovery.get_project_components(project_id)

        # Generate tests for each component
        for component in components:
            if "smoke" in test_types:
                self._generate_smoke_tests(suite, component)

            if "api" in test_types:
                self._generate_api_tests(suite, component)

            if "form" in test_types:
                self._generate_form_tests(suite, component)

            if "query" in test_types:
                self._generate_query_tests(suite, component)

        self.db.commit()
        return suite

    def _generate_smoke_tests(self, suite: TestSuite, component: ComponentInfo):
        """Generate smoke tests (page loads successfully)"""
        # Only for page components
        if component.component_type not in ['page', 'layout']:
            return

        test = TestCase(
            suite_id=suite.id,
            component_id=component.id,
            name=f"Smoke: {component.component_name} loads",
            description=f"Verify {component.file_path} loads without errors",
            test_type="smoke",
            target=f"/{component.file_path.replace('.q', '')}",
            method="GET",
            assertions_json=json.dumps([
                {"type": "status", "operator": "eq", "value": 200},
                {"type": "no_errors", "value": True}
            ]),
            auto_generated=True,
            generation_source=f"component:{component.file_path}"
        )
        self.db.add(test)

    def _generate_api_tests(self, suite: TestSuite, component: ComponentInfo):
        """Generate API tests for each action"""
        actions = json.loads(component.actions_json or "[]")

        for action in actions:
            # Generate success case
            test = TestCase(
                suite_id=suite.id,
                component_id=component.id,
                name=f"API: {action['name']} - success",
                description=f"Test {action['name']} action with valid input",
                test_type="api",
                target=f"/{component.file_path.replace('.q', '')}",
                method=action.get('method', 'POST'),
                input_json=json.dumps(self._generate_valid_input(action)),
                assertions_json=json.dumps([
                    {"type": "status", "operator": "in", "value": [200, 201, 302]},
                    {"type": "no_errors", "value": True}
                ]),
                auto_generated=True,
                generation_source=f"action:{action['name']}"
            )
            self.db.add(test)

            # Generate validation error case
            if action.get('params'):
                test_invalid = TestCase(
                    suite_id=suite.id,
                    component_id=component.id,
                    name=f"API: {action['name']} - invalid input",
                    description=f"Test {action['name']} with missing required fields",
                    test_type="api",
                    target=f"/{component.file_path.replace('.q', '')}",
                    method=action.get('method', 'POST'),
                    input_json=json.dumps({}),  # Empty input
                    assertions_json=json.dumps([
                        {"type": "status", "operator": "in", "value": [400, 422]},
                    ]),
                    auto_generated=True,
                    generation_source=f"action:{action['name']}:invalid"
                )
                self.db.add(test_invalid)

    def _generate_form_tests(self, suite: TestSuite, component: ComponentInfo):
        """Generate form validation tests"""
        forms = json.loads(component.forms_json or "[]")

        for form in forms:
            # Test form submission
            test = TestCase(
                suite_id=suite.id,
                component_id=component.id,
                name=f"Form: {form.get('id', 'form')} - submit",
                description=f"Test form submission with valid data",
                test_type="form",
                target=f"/{component.file_path.replace('.q', '')}",
                method="POST",
                input_json=json.dumps(self._generate_form_data(form)),
                assertions_json=json.dumps([
                    {"type": "status", "operator": "in", "value": [200, 201, 302]}
                ]),
                auto_generated=True,
                generation_source=f"form:{form.get('id')}"
            )
            self.db.add(test)

    def _generate_query_tests(self, suite: TestSuite, component: ComponentInfo):
        """Generate database query tests"""
        queries = json.loads(component.queries_json or "[]")

        for query in queries:
            test = TestCase(
                suite_id=suite.id,
                component_id=component.id,
                name=f"Query: {query.get('name', 'query')} - executes",
                description=f"Verify query executes without SQL errors",
                test_type="query",
                target=query.get('datasource'),
                input_json=json.dumps({"sql": query.get('sql')}),
                assertions_json=json.dumps([
                    {"type": "no_sql_error", "value": True},
                    {"type": "returns_data", "value": True}
                ]),
                auto_generated=True,
                generation_source=f"query:{query.get('name')}"
            )
            self.db.add(test)

    def _generate_valid_input(self, action: Dict) -> Dict:
        """Generate valid input data for an action"""
        input_data = {}
        for param in action.get('params', []):
            param_type = param.get('type', 'string')
            if param_type == 'string':
                input_data[param['name']] = f"test_{param['name']}"
            elif param_type == 'email':
                input_data[param['name']] = "test@example.com"
            elif param_type == 'number':
                input_data[param['name']] = 123
            elif param_type == 'boolean':
                input_data[param['name']] = True
        return input_data

    def _generate_form_data(self, form: Dict) -> Dict:
        """Generate valid form data"""
        data = {}
        for field in form.get('fields', []):
            field_type = field.get('type', 'text')
            if field_type == 'email':
                data[field['name']] = "test@example.com"
            elif field_type == 'password':
                data[field['name']] = "TestPass123!"
            elif field_type == 'number':
                data[field['name']] = "123"
            else:
                data[field['name']] = f"test_{field['name']}"
        return data
```

### 2.5 Test Runner Service

```python
# quantum_admin/backend/test_runner.py (~350 linhas)

class TestRunnerService:
    """Executes test suites against environments"""

    def __init__(self, db: Session):
        self.db = db

    async def run_suite(
        self,
        suite_id: int,
        environment_id: int = None,
        triggered_by: str = "manual"
    ) -> TestRun:
        """
        Execute a test suite.

        Args:
            suite_id: Test suite to run
            environment_id: Target environment (or local if None)
            triggered_by: What triggered the run

        Returns:
            TestRun with results
        """
        suite = self.db.query(TestSuite).get(suite_id)
        if not suite:
            raise ValueError(f"Suite {suite_id} not found")

        # Create run record
        run = TestRun(
            suite_id=suite_id,
            environment_id=environment_id,
            status="running",
            triggered_by=triggered_by,
            started_at=datetime.utcnow()
        )
        self.db.add(run)
        self.db.flush()

        # Get base URL for environment
        base_url = self._get_base_url(environment_id)

        # Get all active test cases
        test_cases = self.db.query(TestCase).filter(
            TestCase.suite_id == suite_id,
            TestCase.is_active == True
        ).order_by(TestCase.order).all()

        run.total_tests = len(test_cases)

        # Execute tests
        results = []
        for test_case in test_cases:
            result = await self._execute_test(test_case, base_url, run.id)
            results.append(result)

            # Update counters
            if result.status == "passed":
                run.passed += 1
            elif result.status == "failed":
                run.failed += 1
            elif result.status == "skipped":
                run.skipped += 1
            else:
                run.errors += 1

        # Finalize run
        run.finished_at = datetime.utcnow()
        run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
        run.status = "passed" if run.failed == 0 and run.errors == 0 else "failed"

        self.db.commit()
        return run

    async def _execute_test(
        self,
        test_case: TestCase,
        base_url: str,
        run_id: int
    ) -> TestResult:
        """Execute a single test case"""
        import httpx

        result = TestResult(
            run_id=run_id,
            test_case_id=test_case.id,
            started_at=datetime.utcnow()
        )

        try:
            url = f"{base_url}{test_case.target}"

            async with httpx.AsyncClient(timeout=test_case.timeout) as client:
                if test_case.method == "GET":
                    response = await client.get(url)
                else:
                    input_data = json.loads(test_case.input_json or "{}")
                    response = await client.request(
                        test_case.method,
                        url,
                        json=input_data
                    )

            # Store response
            result.response_json = json.dumps({
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text[:10000]  # Limit size
            })

            # Run assertions
            assertions = json.loads(test_case.assertions_json or "[]")
            assertion_results = self._run_assertions(assertions, response)
            result.assertion_results_json = json.dumps(assertion_results)

            # Determine status
            all_passed = all(a["passed"] for a in assertion_results)
            result.status = "passed" if all_passed else "failed"

            if not all_passed:
                failed = [a for a in assertion_results if not a["passed"]]
                result.error_message = f"Assertions failed: {failed}"

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)

        result.finished_at = datetime.utcnow()
        result.duration_ms = int((result.finished_at - result.started_at).total_seconds() * 1000)

        self.db.add(result)
        return result

    def _run_assertions(self, assertions: List[Dict], response) -> List[Dict]:
        """Run assertion checks against response"""
        results = []

        for assertion in assertions:
            a_type = assertion.get("type")
            expected = assertion.get("value")
            operator = assertion.get("operator", "eq")

            passed = False
            actual = None

            if a_type == "status":
                actual = response.status_code
                if operator == "eq":
                    passed = actual == expected
                elif operator == "in":
                    passed = actual in expected

            elif a_type == "contains":
                actual = expected in response.text
                passed = actual

            elif a_type == "no_errors":
                # Check for common error patterns
                error_patterns = ["Error", "Exception", "Traceback", "500"]
                actual = not any(p in response.text for p in error_patterns)
                passed = actual == expected

            results.append({
                "assertion": f"{a_type} {operator} {expected}",
                "passed": passed,
                "actual": actual
            })

        return results

    def _get_base_url(self, environment_id: int = None) -> str:
        """Get base URL for environment"""
        if not environment_id:
            return "http://localhost:8000"

        env = self.db.query(Environment).get(environment_id)
        if not env:
            raise ValueError(f"Environment {environment_id} not found")

        host = env.docker_host.replace("ssh://", "").split("@")[-1] if env.docker_host else "localhost"
        return f"http://{host}:{env.port}"

    def get_run_results(self, run_id: int) -> Dict:
        """Get detailed results for a test run"""
        run = self.db.query(TestRun).get(run_id)
        if not run:
            return None

        results = self.db.query(TestResult).filter(
            TestResult.run_id == run_id
        ).all()

        return {
            "run": run.to_dict() if hasattr(run, 'to_dict') else {
                "id": run.id,
                "status": run.status,
                "total": run.total_tests,
                "passed": run.passed,
                "failed": run.failed,
                "duration_ms": run.duration_ms
            },
            "results": [
                {
                    "test_name": r.test_case.name,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "error": r.error_message
                }
                for r in results
            ]
        }
```

### 2.6 Test Dashboard UI

```
┌─────────────────────────────────────────────────────────────────┐
│  Test Suite: QuantumBlog                           [Run All ▶]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── Components Discovered ──────────────────────────────────┐│
│  │                                                             ││
│  │  📄 components/login.q          3 actions, 1 form, 2 queries││
│  │  📄 components/admin.q          5 actions, 2 forms, 4 queries│
│  │  📄 components/post.q           2 actions, 0 forms, 3 queries││
│  │  📄 components/search.q         1 action,  1 form, 1 query  ││
│  │                                                             ││
│  │  Total: 4 components | 11 actions | 4 forms | 10 queries   ││
│  │                                    [Rescan] [Generate Tests]││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─── Test Cases ─────────────────────────────────────────────┐│
│  │                                                             ││
│  │  Type    │ Name                              │ Last Result  ││
│  │  ────────┼───────────────────────────────────┼───────────── ││
│  │  🔥 Smoke │ login.q loads                    │ ● Passed     ││
│  │  🔥 Smoke │ admin.q loads                    │ ● Passed     ││
│  │  🌐 API   │ login action - success           │ ● Passed     ││
│  │  🌐 API   │ login action - invalid           │ ● Passed     ││
│  │  🌐 API   │ createPost action - success      │ ○ Failed     ││
│  │  📝 Form  │ login-form submit                │ ● Passed     ││
│  │  🗃️ Query │ getUser executes                 │ ● Passed     ││
│  │                                                             ││
│  │  [+ Add Test]                                               ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─── Run History ────────────────────────────────────────────┐│
│  │                                                             ││
│  │  Run #5  │ Production │ 2 min ago │ 18/20 ✓ │ 2 ✗ │ [View] ││
│  │  Run #4  │ Staging    │ 1 hr ago  │ 20/20 ✓ │ 0 ✗ │ [View] ││
│  │  Run #3  │ Dev        │ 3 hr ago  │ 19/20 ✓ │ 1 ✗ │ [View] ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌─── Environment Comparison ─────────────────────────────────┐│
│  │                                                             ││
│  │         Dev        Staging      Production                  ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                  ││
│  │  │  19/20   │  │  20/20   │  │  18/20   │                  ││
│  │  │   95%    │  │  100%    │  │   90%    │                  ││
│  │  │  ● Pass  │  │  ● Pass  │  │  ○ Fail  │                  ││
│  │  └──────────┘  └──────────┘  └──────────┘                  ││
│  │                                                             ││
│  │  Failing in Production:                                     ││
│  │  - createPost action (Auth error)                          ││
│  │  - deletePost action (Permission denied)                   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## Parte 3: Integracao CI/CD

### 3.1 Pipeline Hooks

```python
# quantum_admin/backend/pipeline_service.py (adicionar)

class PipelineService:
    # ... existing code ...

    async def _step_test(self, ctx: PipelineContext) -> bool:
        """Run tests before deploy"""
        test_runner = TestRunnerService(self.db)

        # Find active test suite for project
        suite = self.db.query(TestSuite).filter(
            TestSuite.project_id == ctx.project_id,
            TestSuite.auto_run == True,
            TestSuite.is_active == True
        ).first()

        if not suite:
            ctx.log("No auto-run test suite configured, skipping tests")
            return True

        ctx.log(f"Running test suite: {suite.name}")

        # Run tests against target environment
        run = await test_runner.run_suite(
            suite.id,
            ctx.environment_id,
            triggered_by=f"deploy:{ctx.deployment_id}"
        )

        ctx.log(f"Tests completed: {run.passed}/{run.total_tests} passed")

        if run.status == "failed":
            ctx.log(f"Tests failed! {run.failed} failures, {run.errors} errors")
            # Optionally block deploy
            if suite.config.get("block_on_failure", True):
                return False

        return True
```

### 3.2 Webhook Integration

```python
# quantum_admin/backend/webhook_service.py (adicionar)

class WebhookService:
    # ... existing code ...

    async def process_github_push(self, payload: Dict) -> Optional[Deployment]:
        # ... existing code ...

        # After deploy, run tests
        if deployment and deployment.status == "completed":
            await self._trigger_tests(deployment.project_id, deployment.environment_id)

    async def _trigger_tests(self, project_id: int, environment_id: int):
        """Trigger test run after successful deploy"""
        test_runner = TestRunnerService(self.db)

        suite = self.db.query(TestSuite).filter(
            TestSuite.project_id == project_id,
            TestSuite.auto_run == True
        ).first()

        if suite:
            await test_runner.run_suite(
                suite.id,
                environment_id,
                triggered_by="webhook:post-deploy"
            )
```

---

## Parte 4: Ordem de Implementacao

### Fase 1: Resource Manager Core (4h)
1. Criar modelos: PortAllocation, PortRange, Secret, ServiceRegistry
2. Implementar PortManager com allocate/release/reserve
3. Implementar SecretManager com encrypt/decrypt
4. Adicionar endpoints API basicos
5. UI basica na pagina Settings

### Fase 2: Service Discovery (2h)
1. Implementar ServiceRegistryManager
2. Health check async para todos os servicos
3. Integracao com Environment creation
4. Dashboard de servicos

### Fase 3: Config Generation (2h)
1. Implementar ConfigGenerator
2. Gerar .env files
3. Gerar docker-compose.yml
4. Gerar nginx.conf
5. Download buttons na UI

### Fase 4: Component Discovery (3h)
1. Criar modelo ComponentInfo
2. Implementar scanner de arquivos .q
3. Parser para extrair actions/queries/forms
4. UI de componentes descobertos
5. Endpoint de rescan

### Fase 5: Test Generator (3h)
1. Criar modelos TestSuite, TestCase
2. Implementar geradores: smoke, api, form, query
3. UI para gerenciar test cases
4. Edicao manual de testes

### Fase 6: Test Runner (4h)
1. Criar modelos TestRun, TestResult
2. Implementar executor async
3. Assertions engine
4. Resultados e historico
5. Comparacao entre environments

### Fase 7: CI/CD Integration (2h)
1. Hook no pipeline de deploy
2. Block deploy se testes falham
3. Webhook triggers
4. Notifications

---

## Arquivos a Criar

| Arquivo | Linhas | Descricao |
|---------|--------|-----------|
| `resource_manager.py` | ~500 | Gerenciador centralizado |
| `port_manager.py` | ~200 | Alocacao de portas |
| `secret_manager.py` | ~150 | Gerenciamento de secrets |
| `service_registry.py` | ~200 | Service discovery |
| `config_generator.py` | ~300 | Geracao de configs |
| `component_discovery.py` | ~300 | Scanner de componentes |
| `test_generator.py` | ~400 | Geracao de testes |
| `test_runner.py` | ~350 | Execucao de testes |

## Arquivos a Modificar

| Arquivo | Mudancas |
|---------|----------|
| `models.py` | +8 novos modelos |
| `main.py` | +30 endpoints |
| `pipeline_service.py` | Hook de testes |
| `environment_service.py` | Integracao com port manager |

---

## Verificacao

```bash
# 1. Alocar porta
curl -X POST "http://localhost:8001/resources/ports/allocate" \
  -d '{"service_name": "myapp", "port_type": "app", "host": "forge"}'
# Returns: {"port": 8083}

# 2. Descobrir componentes
curl -X POST "http://localhost:8001/projects/2/components/scan"
# Returns: {"components": [...], "stats": {...}}

# 3. Gerar suite de testes
curl -X POST "http://localhost:8001/projects/2/test-suites/generate" \
  -d '{"name": "Auto Suite", "types": ["smoke", "api"]}'

# 4. Executar testes
curl -X POST "http://localhost:8001/test-suites/1/run" \
  -d '{"environment_id": 2}'
# Returns: {"run_id": 5, "status": "running"}

# 5. Ver resultados
curl "http://localhost:8001/test-runs/5"
# Returns: {"passed": 18, "failed": 2, "results": [...]}
```
