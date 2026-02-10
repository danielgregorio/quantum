"""
SQLAlchemy models for Quantum Admin
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Project(Base):
    """Project represents a Quantum application"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    status = Column(String(50), default='active')  # active, inactive

    # Source Code Configuration
    source_path = Column(String(512))  # Local path to source code (e.g., /home/user/projects/myapp)
    git_url = Column(String(512))      # Git repository URL (e.g., https://github.com/user/repo.git)
    git_branch = Column(String(100), default='main')  # Default branch to use

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datasources = relationship("Datasource", back_populates="project", cascade="all, delete-orphan")
    components = relationship("Component", back_populates="project", cascade="all, delete-orphan")
    endpoints = relationship("Endpoint", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"


class Datasource(Base):
    """Datasource represents a database connection (Docker or direct)"""
    __tablename__ = 'datasources'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # postgres, mysql, mongodb
    connection_type = Column(String(50), nullable=False)  # docker, direct

    # Docker-specific fields
    container_id = Column(String(255))
    image = Column(String(255))
    port = Column(Integer)

    # Connection details
    host = Column(String(255))
    database_name = Column(String(255))
    username = Column(String(255))
    password_encrypted = Column(Text)  # Encrypted password

    # Status
    status = Column(String(50), default='stopped')  # running, stopped, error
    health_status = Column(String(50), default='unknown')  # healthy, unhealthy, unknown
    setup_status = Column(String(50), default='pending')  # pending, configuring, ready, error
    auto_start = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="datasources")
    migrations = relationship("Migration", back_populates="datasource", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Datasource(id={self.id}, name='{self.name}', type='{self.type}', status='{self.status}')>"


class Migration(Base):
    """Migration tracks schema changes for datasources"""
    __tablename__ = 'migrations'

    id = Column(Integer, primary_key=True)
    datasource_id = Column(Integer, ForeignKey('datasources.id'), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    sql_content = Column(Text, nullable=False)
    applied_at = Column(DateTime)
    status = Column(String(50), default='pending')  # pending, applied, failed, rolled_back
    error_message = Column(Text)

    # Relationships
    datasource = relationship("Datasource", back_populates="migrations")

    def __repr__(self):
        return f"<Migration(id={self.id}, version='{self.version}', status='{self.status}')>"


class Component(Base):
    """Component represents a .q file in a project"""
    __tablename__ = 'components'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    status = Column(String(50), default='unknown')  # active, error, inactive, unknown
    error_message = Column(Text)
    last_compiled = Column(DateTime)

    # Metadata counters (cached from parsing)
    function_count = Column(Integer, default=0)
    endpoint_count = Column(Integer, default=0)
    query_count = Column(Integer, default=0)

    # Test tracking
    test_count = Column(Integer, default=0)        # Total tests associated
    tests_passing = Column(Integer, default=0)     # Tests passing
    tests_failing = Column(Integer, default=0)     # Tests failing
    last_test_run_id = Column(Integer, ForeignKey('test_runs.id'), nullable=True)
    last_test_run_at = Column(DateTime)

    # Relationships
    project = relationship("Project", back_populates="components")
    endpoints = relationship("Endpoint", back_populates="component")
    last_test_run = relationship("TestRun", foreign_keys=[last_test_run_id])
    tests = relationship("ComponentTest", back_populates="component", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Component(id={self.id}, name='{self.name}', status='{self.status}')>"

    @property
    def has_tests(self) -> bool:
        return self.test_count > 0

    @property
    def test_coverage(self) -> int:
        """Return test coverage percentage (0-100)"""
        if self.test_count == 0:
            return 0
        return int((self.tests_passing / self.test_count) * 100) if self.test_count > 0 else 0


class Endpoint(Base):
    """Endpoint represents a REST API endpoint defined in a component"""
    __tablename__ = 'endpoints'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey('components.id'))
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH
    path = Column(String(512), nullable=False)
    function_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Relationships
    project = relationship("Project", back_populates="endpoints")
    component = relationship("Component", back_populates="endpoints")

    def __repr__(self):
        return f"<Endpoint(id={self.id}, method='{self.method}', path='{self.path}')>"


class TestRun(Base):
    """TestRun represents a test execution session"""
    __tablename__ = 'test_runs'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    status = Column(String(50), default='running')  # running, completed, failed, cancelled
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    duration_seconds = Column(Integer)
    triggered_by = Column(String(255))  # user, ci/cd, schedule
    suite_filter = Column(String(255))  # Optional suite name filter
    error_message = Column(Text)

    # Relationships
    project = relationship("Project", backref="test_runs")
    test_results = relationship("TestResult", back_populates="test_run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestRun(id={self.id}, status='{self.status}', passed={self.passed_tests}/{self.total_tests})>"


class TestResult(Base):
    """TestResult represents individual test execution results"""
    __tablename__ = 'test_results'

    id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey('test_runs.id'), nullable=False, index=True)
    suite_name = Column(String(255), nullable=False)
    test_file = Column(String(512), nullable=False)
    status = Column(String(50), nullable=False)  # passed, failed, error, skipped
    duration_seconds = Column(Integer)
    error_message = Column(Text)
    output = Column(Text)

    # Relationships
    test_run = relationship("TestRun", back_populates="test_results")

    def __repr__(self):
        return f"<TestResult(id={self.id}, suite='{self.suite_name}', status='{self.status}')>"


class ComponentTest(Base):
    """ComponentTest tracks tests associated with components"""
    __tablename__ = 'component_tests'

    id = Column(Integer, primary_key=True)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False, index=True)

    # Test info
    test_file = Column(String(512), nullable=False)    # tests/test_user_login.py
    test_name = Column(String(255), nullable=False)    # test_login_success
    test_type = Column(String(50), default='unit')     # unit, integration, api, e2e

    # Generation info
    generated_at = Column(DateTime)
    generated_by = Column(String(50))                  # auto, manual

    # Last execution
    last_run_id = Column(Integer, ForeignKey('test_runs.id'), nullable=True)
    last_status = Column(String(50))                   # passed, failed, skipped, pending
    last_run_at = Column(DateTime)
    last_duration_seconds = Column(Integer)
    last_error_message = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    component = relationship("Component", back_populates="tests")
    last_run = relationship("TestRun", foreign_keys=[last_run_id])

    def __repr__(self):
        return f"<ComponentTest(id={self.id}, name='{self.test_name}', status='{self.last_status}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "component_id": self.component_id,
            "test_file": self.test_file,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "generated_by": self.generated_by,
            "last_status": self.last_status,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_duration_seconds": self.last_duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class EnvironmentVariable(Base):
    """EnvironmentVariable represents a project environment variable or secret"""
    __tablename__ = 'environment_variables'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    value_encrypted = Column(Text, nullable=False)  # Encrypted value
    description = Column(Text)
    is_secret = Column(Boolean, default=False)  # If true, value is masked in UI
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="environment_variables")

    def __repr__(self):
        return f"<EnvironmentVariable(id={self.id}, key='{self.key}', is_secret={self.is_secret})>"


class ConfigurationHistory(Base):
    """ConfigurationHistory tracks changes to project configuration"""
    __tablename__ = 'configuration_history'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    changed_by = Column(String(255))  # user, api, system
    changes_json = Column(Text)  # JSON describing what changed
    snapshot_json = Column(Text)  # Full configuration snapshot

    # Relationships
    project = relationship("Project", backref="configuration_history")

    def __repr__(self):
        return f"<ConfigurationHistory(id={self.id}, project_id={self.project_id}, version={self.version})>"


class Connector(Base):
    """Connector represents an infrastructure connection (database, queue, cache, storage, AI)"""
    __tablename__ = 'connectors'

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # database, mq, cache, storage, ai
    provider = Column(String(50), nullable=False)  # postgres, mysql, rabbitmq, redis, s3, ollama, etc.
    host = Column(String(255), default='localhost')
    port = Column(Integer, default=0)
    username = Column(String(255), default='')
    password_encrypted = Column(Text, default='')  # Encrypted password/API key
    database = Column(String(255), default='')  # or bucket, vhost, etc.
    options_json = Column(Text, default='{}')  # JSON for provider-specific options
    is_default = Column(Boolean, default=False)
    docker_auto = Column(Boolean, default=False)
    docker_image = Column(String(255), default='')
    docker_container_id = Column(String(255), default='')
    status = Column(String(50), default='unknown')  # unknown, connected, disconnected, error
    last_tested = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Scope: public (available to all apps) or application (exclusive to one app)
    scope = Column(String(50), default='public')  # "public" or "application"
    application_id = Column(Integer, ForeignKey('projects.id'), nullable=True)

    # Relationship to application (Project)
    application = relationship("Project", backref="connectors")

    def __repr__(self):
        scope_info = f"app={self.application_id}" if self.scope == 'application' else 'public'
        return f"<Connector(id={self.id}, name='{self.name}', {scope_info})>"


class DeploymentTarget(Base):
    """DeploymentTarget represents a deployment destination"""
    __tablename__ = 'deployment_targets'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # local, docker, ssh, kubernetes
    config_json = Column(Text)  # JSON configuration for target (host, port, paths, etc.)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="deployment_targets")
    deployments = relationship("Deployment", back_populates="target", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DeploymentTarget(id={self.id}, name='{self.name}', type='{self.type}')>"


class Deployment(Base):
    """Deployment represents a deployment execution"""
    __tablename__ = 'deployments'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey('deployment_targets.id'), nullable=False, index=True)
    version = Column(String(100))  # Git commit, tag, or version number
    status = Column(String(50), default='pending')  # pending, building, deploying, completed, failed, rolled_back
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    triggered_by = Column(String(255))  # user, ci/cd, schedule
    build_log = Column(Text)
    deploy_log = Column(Text)
    error_message = Column(Text)
    rollback_from = Column(Integer)  # ID of deployment being rolled back

    # Relationships
    project = relationship("Project", backref="deployments")
    target = relationship("DeploymentTarget", back_populates="deployments")
    versions = relationship("DeploymentVersion", back_populates="deployment")

    def __repr__(self):
        return f"<Deployment(id={self.id}, version='{self.version}', status='{self.status}')>"


class Environment(Base):
    """Environment represents a deployment environment (dev, staging, production)"""
    __tablename__ = 'environments'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    name = Column(String(50), nullable=False)           # dev, staging, production
    display_name = Column(String(100))                  # Development, Staging, Production
    order = Column(Integer, default=1)                  # 1, 2, 3 (promotion order)

    # Deployment Config
    docker_host = Column(String(255))                   # ssh://user@host or unix://
    docker_registry = Column(String(255))
    deploy_path = Column(String(512))                   # /var/www/app
    container_name = Column(String(100))
    port = Column(Integer)

    # Git Config
    branch = Column(String(100), default='main')        # main, staging, develop
    auto_deploy = Column(Boolean, default=False)        # Deploy on push to branch

    # Approval
    requires_approval = Column(Boolean, default=False)  # Gate for production
    approved_by = Column(String(255))                   # Last approver

    # Health Check
    health_url = Column(String(512))                    # http://host:port/health
    health_timeout = Column(Integer, default=30)

    # Secrets (env vars for this environment)
    env_vars_json = Column(Text)                        # {"DB_HOST": "prod-db.example.com"}

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="environments")
    deployment_versions = relationship("DeploymentVersion", back_populates="environment")

    def __repr__(self):
        return f"<Environment(id={self.id}, name='{self.name}', project_id={self.project_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "display_name": self.display_name,
            "order": self.order,
            "docker_host": self.docker_host,
            "docker_registry": self.docker_registry,
            "deploy_path": self.deploy_path,
            "container_name": self.container_name,
            "port": self.port,
            "branch": self.branch,
            "auto_deploy": self.auto_deploy,
            "requires_approval": self.requires_approval,
            "health_url": self.health_url,
            "health_timeout": self.health_timeout,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class DeploymentVersion(Base):
    """DeploymentVersion tracks deployed versions with git and docker info"""
    __tablename__ = 'deployment_versions'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=False, index=True)

    # Git Info
    git_commit = Column(String(40))                     # Full SHA
    git_branch = Column(String(100))
    git_message = Column(Text)                          # Commit message
    git_author = Column(String(255))

    # Docker Info
    docker_image = Column(String(255))                  # registry/app:commit-sha
    docker_tag = Column(String(100))                    # commit-sha or latest

    # Deploy Status
    deployment_id = Column(Integer, ForeignKey('deployments.id'))
    is_current = Column(Boolean, default=False)         # Currently deployed version
    is_rollback_target = Column(Boolean, default=True)  # Available for rollback

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="deployment_versions")
    environment = relationship("Environment", back_populates="deployment_versions")
    deployment = relationship("Deployment", back_populates="versions")

    def __repr__(self):
        return f"<DeploymentVersion(id={self.id}, commit='{self.git_commit[:7] if self.git_commit else 'N/A'}', env={self.environment_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "git_message": self.git_message,
            "git_author": self.git_author,
            "docker_image": self.docker_image,
            "docker_tag": self.docker_tag,
            "deployment_id": self.deployment_id,
            "is_current": self.is_current,
            "is_rollback_target": self.is_rollback_target,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WebhookEvent(Base):
    """WebhookEvent tracks incoming webhook events from GitHub/GitLab"""
    __tablename__ = 'webhook_events'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)

    # Event Info
    provider = Column(String(50), nullable=False)       # github, gitlab, bitbucket
    event_type = Column(String(50), nullable=False)     # push, pull_request, tag
    payload_json = Column(Text)

    # Git Info
    branch = Column(String(100))
    commit = Column(String(40))
    author = Column(String(255))
    message = Column(Text)

    # Processing
    processed = Column(Boolean, default=False)
    deployment_id = Column(Integer, ForeignKey('deployments.id'))
    error_message = Column(Text)

    received_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="webhook_events")
    deployment = relationship("Deployment", backref="webhook_event")

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, provider='{self.provider}', type='{self.event_type}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "provider": self.provider,
            "event_type": self.event_type,
            "branch": self.branch,
            "commit": self.commit,
            "author": self.author,
            "message": self.message,
            "processed": self.processed,
            "deployment_id": self.deployment_id,
            "error_message": self.error_message,
            "received_at": self.received_at.isoformat() if self.received_at else None
        }


# =============================================================================
# RESOURCE MANAGER MODELS
# =============================================================================

class PortAllocation(Base):
    """Track all port allocations across hosts"""
    __tablename__ = 'port_allocations'

    id = Column(Integer, primary_key=True)

    # What owns this port
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True, index=True)
    service_name = Column(String(100), nullable=False)

    # Port info
    port = Column(Integer, nullable=False)
    port_type = Column(String(50))  # app, database, cache, web, custom
    host = Column(String(255), default='localhost')

    # Status
    status = Column(String(50), default='allocated')  # allocated, reserved, released
    is_reserved = Column(Boolean, default=False)
    reserved_reason = Column(String(255))

    # Metadata
    allocated_at = Column(DateTime, default=datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(String(50))  # healthy, unhealthy, unknown

    # Relationships
    project = relationship("Project", backref="port_allocations")
    environment = relationship("Environment", backref="port_allocations")

    __table_args__ = (
        UniqueConstraint('port', 'host', name='uq_port_host'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "service_name": self.service_name,
            "port": self.port,
            "port_type": self.port_type,
            "host": self.host,
            "status": self.status,
            "is_reserved": self.is_reserved,
            "reserved_reason": self.reserved_reason,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None,
            "health_status": self.health_status
        }


class PortRange(Base):
    """Define port ranges for different service types"""
    __tablename__ = 'port_ranges'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    start_port = Column(Integer, nullable=False)
    end_port = Column(Integer, nullable=False)
    host = Column(String(255), default='*')  # * = all hosts
    description = Column(String(255))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_port": self.start_port,
            "end_port": self.end_port,
            "host": self.host,
            "description": self.description
        }


class Secret(Base):
    """Encrypted secrets storage"""
    __tablename__ = 'secrets'

    id = Column(Integer, primary_key=True)

    # Scope
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True, index=True)
    scope = Column(String(50), default='global')  # global, project, environment

    # Secret data
    key = Column(String(255), nullable=False)
    encrypted_value = Column(Text, nullable=False)

    # Metadata
    description = Column(String(500))
    is_sensitive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_rotated = Column(DateTime)

    # Relationships
    project = relationship("Project", backref="secrets")
    environment = relationship("Environment", backref="secrets")

    def to_dict(self, include_value: bool = False):
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "scope": self.scope,
            "key": self.key,
            "description": self.description,
            "is_sensitive": self.is_sensitive,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None
        }
        if include_value:
            result["encrypted_value"] = self.encrypted_value
        return result


class ServiceRegistry(Base):
    """Service discovery registry"""
    __tablename__ = 'service_registry'

    id = Column(Integer, primary_key=True)

    # Service identity
    name = Column(String(100), nullable=False, unique=True)
    service_type = Column(String(50))  # app, database, cache, queue, gateway

    # Location
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), default='http')

    # Health
    health_endpoint = Column(String(255))
    health_interval = Column(Integer, default=30)
    last_health_check = Column(DateTime)
    health_status = Column(String(50), default='unknown')
    consecutive_failures = Column(Integer, default=0)

    # Metadata
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True, index=True)
    metadata_json = Column(Text)

    registered_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="services")
    environment = relationship("Environment", backref="services")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "health_endpoint": self.health_endpoint,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else {},
            "registered_at": self.registered_at.isoformat() if self.registered_at else None
        }


# =============================================================================
# AUDIT LOG MODEL
# =============================================================================

class AuditLog(Base):
    """Track all user actions for auditing purposes"""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # User info
    user_id = Column(String(100))
    user_ip = Column(String(45))  # IPv6 compatible

    # Action info
    action = Column(String(50), nullable=False)  # create, update, delete, deploy, login, logout, etc.
    resource_type = Column(String(50))  # project, connector, environment, deployment, etc.
    resource_id = Column(Integer)
    resource_name = Column(String(255))

    # Additional context
    details = Column(Text)  # JSON with additional details
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)

    # Request info
    request_method = Column(String(10))
    request_path = Column(String(512))

    # Relationships
    project = relationship("Project", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}:{self.resource_id}')>"

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "user_ip": self.user_ip,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "details": json.loads(self.details) if self.details else None,
            "project_id": self.project_id,
            "request_method": self.request_method,
            "request_path": self.request_path
        }


# =============================================================================
# HEALTH CHECK & INCIDENT MODELS
# =============================================================================

class HealthCheck(Base):
    """Health check configuration for services"""
    __tablename__ = 'health_checks'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True, index=True)

    # Check configuration
    name = Column(String(100), nullable=False)
    endpoint = Column(String(512), nullable=False)
    method = Column(String(10), default='GET')
    expected_status = Column(Integer, default=200)
    timeout_seconds = Column(Integer, default=30)
    interval_seconds = Column(Integer, default=60)

    # Status
    is_active = Column(Boolean, default=True)
    last_check = Column(DateTime)
    last_status = Column(String(50))  # healthy, unhealthy, unknown
    consecutive_failures = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", backref="health_checks")
    environment = relationship("Environment", backref="health_checks")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "method": self.method,
            "expected_status": self.expected_status,
            "timeout_seconds": self.timeout_seconds,
            "interval_seconds": self.interval_seconds,
            "is_active": self.is_active,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_status": self.last_status,
            "consecutive_failures": self.consecutive_failures
        }


class Incident(Base):
    """Track health check incidents"""
    __tablename__ = 'incidents'

    id = Column(Integer, primary_key=True)
    health_check_id = Column(Integer, ForeignKey('health_checks.id'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True, index=True)

    # Incident details
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime)
    status = Column(String(50), default='active')  # active, resolved, acknowledged

    # Error info
    error_message = Column(Text)
    error_code = Column(Integer)
    response_time_ms = Column(Integer)

    # Resolution
    resolved_by = Column(String(100))
    resolution_notes = Column(Text)

    # Relationships
    health_check = relationship("HealthCheck", backref="incidents")
    project = relationship("Project", backref="incidents")

    def to_dict(self):
        return {
            "id": self.id,
            "health_check_id": self.health_check_id,
            "project_id": self.project_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "response_time_ms": self.response_time_ms,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes
        }


# =============================================================================
# APPLICATION LOG MODEL
# =============================================================================

class ApplicationLog(Base):
    """Store application runtime logs"""
    __tablename__ = 'application_logs'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=True, index=True)

    # Log entry
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    source = Column(String(50))  # app, db, access, deploy, system
    message = Column(Text, nullable=False)

    # Context
    component_name = Column(String(255))
    function_name = Column(String(255))
    line_number = Column(Integer)

    # Request context (for access logs)
    request_id = Column(String(50))
    request_method = Column(String(10))
    request_path = Column(String(512))
    response_status = Column(Integer)
    response_time_ms = Column(Integer)

    # Additional data
    extra_data = Column(Text)  # JSON

    # Relationships
    project = relationship("Project", backref="application_logs")
    environment = relationship("Environment", backref="application_logs")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "project_id": self.project_id,
            "environment_id": self.environment_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "component_name": self.component_name,
            "function_name": self.function_name,
            "request_id": self.request_id,
            "request_method": self.request_method,
            "request_path": self.request_path,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "extra_data": json.loads(self.extra_data) if self.extra_data else None
        }


# =============================================================================
# CLOUD INTEGRATION MODEL
# =============================================================================

class CloudIntegration(Base):
    """Cloud provider integration configuration"""
    __tablename__ = 'cloud_integrations'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)  # aws, kubernetes, azure, gcp

    # Encrypted credentials (JSON)
    credentials_encrypted = Column(Text, nullable=False)

    # Configuration
    region = Column(String(50))
    default_config_json = Column(Text)  # Default deployment config

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default for deploy
    last_tested = Column(DateTime)
    test_status = Column(String(50))  # success, failed, unknown

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CloudIntegration(id={self.id}, name='{self.name}', provider='{self.provider}')>"

    def to_dict(self, include_credentials: bool = False):
        import json
        result = {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "region": self.region,
            "default_config": json.loads(self.default_config_json) if self.default_config_json else {},
            "is_active": self.is_active,
            "is_default": self.is_default,
            "last_tested": self.last_tested.isoformat() if self.last_tested else None,
            "test_status": self.test_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_credentials:
            result["credentials"] = json.loads(self.credentials_encrypted) if self.credentials_encrypted else {}
        return result
