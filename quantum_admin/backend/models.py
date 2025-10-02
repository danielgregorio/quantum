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
