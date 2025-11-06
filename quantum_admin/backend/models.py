"""
SQLAlchemy models for Quantum Admin
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
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

    # Relationships
    project = relationship("Project", back_populates="components")
    endpoints = relationship("Endpoint", back_populates="component")

    def __repr__(self):
        return f"<Component(id={self.id}, name='{self.name}', status='{self.status}')>"


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
