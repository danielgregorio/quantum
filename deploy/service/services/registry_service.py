"""
Registry Service - SQLite database for tracking deployments
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class App(Base):
    """Application model."""
    __tablename__ = 'apps'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default='pending')
    container_id = Column(String(64), nullable=True)
    image_tag = Column(String(200), nullable=True)
    path = Column(String(500), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    env_vars = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Deployment(Base):
    """Deployment history model."""
    __tablename__ = 'deployments'

    id = Column(Integer, primary_key=True)
    app_name = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class EnvVar(Base):
    """Environment variable model (for encrypted storage)."""
    __tablename__ = 'env_vars'

    id = Column(Integer, primary_key=True)
    app_name = Column(String(100), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)  # Encrypted in production
    is_secret = Column(Integer, default=0)  # 1 if value is sensitive


class RegistryService:
    """Service for managing the deployment registry."""

    _instance = None
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        """Singleton pattern for registry service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize database connection."""
        if self._initialized:
            return

        registry_dir = Path(os.environ.get('QUANTUM_REGISTRY_DIR', '/data/quantum/registry'))
        registry_dir.mkdir(parents=True, exist_ok=True)

        db_path = registry_dir / 'quantum_registry.db'
        self._engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self._SessionLocal = sessionmaker(bind=self._engine)

        self._initialized = True
        logger.info(f"Registry database initialized: {db_path}")

    def init_db(self):
        """Create database tables."""
        Base.metadata.create_all(self._engine)
        logger.info("Database tables created")

    def _get_session(self) -> Session:
        """Get a database session."""
        return self._SessionLocal()

    # App CRUD operations

    def get_app(self, name: str) -> Optional[App]:
        """Get app by name."""
        with self._get_session() as session:
            return session.query(App).filter(App.name == name).first()

    def list_apps(self, status_filter: Optional[str] = None) -> List[App]:
        """List all apps, optionally filtered by status."""
        with self._get_session() as session:
            query = session.query(App)
            if status_filter:
                query = query.filter(App.status == status_filter)
            return query.order_by(App.name).all()

    def upsert_app(
        self,
        name: str,
        container_id: str,
        image_tag: str,
        status: str,
        path: str,
        env_vars: Optional[Dict] = None,
        version: int = 1,
        config: Optional[Dict] = None
    ) -> App:
        """Create or update an app."""
        with self._get_session() as session:
            app = session.query(App).filter(App.name == name).first()

            if app:
                # Update existing
                app.container_id = container_id
                app.image_tag = image_tag
                app.status = status
                app.path = path
                app.env_vars = env_vars
                app.version = version
                app.config = config
                app.updated_at = datetime.utcnow()
            else:
                # Create new
                app = App(
                    name=name,
                    container_id=container_id,
                    image_tag=image_tag,
                    status=status,
                    path=path,
                    env_vars=env_vars,
                    version=version,
                    config=config
                )
                session.add(app)

            session.commit()
            session.refresh(app)
            logger.info(f"App {name} saved (version {version})")
            return app

    def update_app_status(self, name: str, status: str) -> bool:
        """Update app status."""
        with self._get_session() as session:
            app = session.query(App).filter(App.name == name).first()
            if app:
                app.status = status
                app.updated_at = datetime.utcnow()
                session.commit()
                logger.info(f"App {name} status updated to {status}")
                return True
            return False

    def delete_app(self, name: str) -> bool:
        """Delete an app from registry."""
        with self._get_session() as session:
            app = session.query(App).filter(App.name == name).first()
            if app:
                # Also delete env vars and deployment logs
                session.query(EnvVar).filter(EnvVar.app_name == name).delete()
                session.query(Deployment).filter(Deployment.app_name == name).delete()
                session.delete(app)
                session.commit()
                logger.info(f"App {name} deleted from registry")
                return True
            return False

    # Deployment logging

    def log_deployment(
        self,
        app_name: str,
        version: int,
        status: str,
        message: str
    ) -> Deployment:
        """Log a deployment event."""
        with self._get_session() as session:
            deployment = Deployment(
                app_name=app_name,
                version=version,
                status=status,
                message=message
            )
            session.add(deployment)
            session.commit()
            session.refresh(deployment)
            logger.info(f"Deployment logged: {app_name} v{version} - {status}")
            return deployment

    def get_deployment_logs(
        self,
        app_name: str,
        limit: int = 10
    ) -> List[Deployment]:
        """Get deployment history for an app."""
        with self._get_session() as session:
            return session.query(Deployment) \
                .filter(Deployment.app_name == app_name) \
                .order_by(Deployment.timestamp.desc()) \
                .limit(limit) \
                .all()

    # Environment variables

    def set_env_var(
        self,
        app_name: str,
        key: str,
        value: str,
        is_secret: bool = False
    ):
        """Set an environment variable for an app."""
        with self._get_session() as session:
            env_var = session.query(EnvVar) \
                .filter(EnvVar.app_name == app_name, EnvVar.key == key) \
                .first()

            if env_var:
                env_var.value = value
                env_var.is_secret = 1 if is_secret else 0
            else:
                env_var = EnvVar(
                    app_name=app_name,
                    key=key,
                    value=value,
                    is_secret=1 if is_secret else 0
                )
                session.add(env_var)

            session.commit()
            logger.info(f"Env var {key} set for {app_name}")

    def get_env_vars(self, app_name: str) -> Dict[str, str]:
        """Get all environment variables for an app."""
        with self._get_session() as session:
            env_vars = session.query(EnvVar) \
                .filter(EnvVar.app_name == app_name) \
                .all()
            return {ev.key: ev.value for ev in env_vars}

    def delete_env_var(self, app_name: str, key: str) -> bool:
        """Delete an environment variable."""
        with self._get_session() as session:
            result = session.query(EnvVar) \
                .filter(EnvVar.app_name == app_name, EnvVar.key == key) \
                .delete()
            session.commit()
            return result > 0

    # Statistics

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._get_session() as session:
            total_apps = session.query(App).count()
            running_apps = session.query(App).filter(App.status == 'running').count()
            stopped_apps = session.query(App).filter(App.status == 'stopped').count()
            failed_apps = session.query(App).filter(App.status == 'failed').count()
            total_deployments = session.query(Deployment).count()

            return {
                'total_apps': total_apps,
                'running_apps': running_apps,
                'stopped_apps': stopped_apps,
                'failed_apps': failed_apps,
                'total_deployments': total_deployments
            }
