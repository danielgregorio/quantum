"""
Environment Service for Quantum Admin
Handles deployment environment CRUD operations
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from .models import Environment, Project
    from .database import get_db, SessionLocal
except ImportError:
    from models import Environment, Project
    from database import get_db, SessionLocal


class EnvironmentService:
    """Service for managing deployment environments"""

    def __init__(self, db: Session = None):
        """
        Initialize environment service

        Args:
            db: SQLAlchemy session (optional, creates new if not provided)
        """
        self._db = db
        self._own_session = db is None

    @property
    def db(self) -> Session:
        """Get database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        """Close database session if we own it"""
        if self._own_session and self._db:
            self._db.close()
            self._db = None

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create_environment(self, project_id: int, data: Dict[str, Any]) -> Environment:
        """
        Create a new environment

        Args:
            project_id: Project ID
            data: Environment data dict

        Returns:
            Created Environment object
        """
        # Verify project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Determine order if not specified
        if "order" not in data:
            max_order = self.db.query(Environment).filter(
                Environment.project_id == project_id
            ).count()
            data["order"] = max_order + 1

        # Handle env_vars
        env_vars = data.pop("env_vars", None)
        if env_vars and isinstance(env_vars, dict):
            data["env_vars_json"] = json.dumps(env_vars)

        env = Environment(
            project_id=project_id,
            name=data.get("name"),
            display_name=data.get("display_name") or data.get("name", "").title(),
            order=data.get("order", 1),
            docker_host=data.get("docker_host"),
            docker_registry=data.get("docker_registry"),
            deploy_path=data.get("deploy_path"),
            container_name=data.get("container_name"),
            port=data.get("port"),
            branch=data.get("branch", "main"),
            auto_deploy=data.get("auto_deploy", False),
            requires_approval=data.get("requires_approval", False),
            health_url=data.get("health_url"),
            health_timeout=data.get("health_timeout", 30),
            env_vars_json=data.get("env_vars_json"),
            is_active=data.get("is_active", True)
        )

        self.db.add(env)
        self.db.commit()
        self.db.refresh(env)

        logger.info(f"Created environment: {env.name} for project {project_id}")
        return env

    def get_environment(self, env_id: int) -> Optional[Environment]:
        """
        Get environment by ID

        Args:
            env_id: Environment ID

        Returns:
            Environment or None
        """
        return self.db.query(Environment).filter(Environment.id == env_id).first()

    def get_environment_by_name(self, project_id: int, name: str) -> Optional[Environment]:
        """
        Get environment by project and name

        Args:
            project_id: Project ID
            name: Environment name (dev, staging, production)

        Returns:
            Environment or None
        """
        return self.db.query(Environment).filter(
            Environment.project_id == project_id,
            Environment.name == name
        ).first()

    def list_environments(self, project_id: int, active_only: bool = True) -> List[Environment]:
        """
        List all environments for a project

        Args:
            project_id: Project ID
            active_only: Only return active environments

        Returns:
            List of environments ordered by order field
        """
        query = self.db.query(Environment).filter(Environment.project_id == project_id)

        if active_only:
            query = query.filter(Environment.is_active == True)

        return query.order_by(Environment.order).all()

    def update_environment(self, env_id: int, data: Dict[str, Any]) -> Optional[Environment]:
        """
        Update an environment

        Args:
            env_id: Environment ID
            data: Fields to update

        Returns:
            Updated Environment or None
        """
        env = self.get_environment(env_id)
        if not env:
            return None

        # Handle env_vars specially
        env_vars = data.pop("env_vars", None)
        if env_vars is not None:
            if isinstance(env_vars, dict):
                data["env_vars_json"] = json.dumps(env_vars)
            elif isinstance(env_vars, str):
                data["env_vars_json"] = env_vars

        # Update allowed fields
        allowed_fields = {
            "name", "display_name", "order", "docker_host", "docker_registry",
            "deploy_path", "container_name", "port", "branch", "auto_deploy",
            "requires_approval", "approved_by", "health_url", "health_timeout",
            "env_vars_json", "is_active"
        }

        for key, value in data.items():
            if key in allowed_fields:
                setattr(env, key, value)

        env.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(env)

        logger.info(f"Updated environment: {env.name}")
        return env

    def delete_environment(self, env_id: int) -> bool:
        """
        Delete an environment

        Args:
            env_id: Environment ID

        Returns:
            True if deleted
        """
        env = self.get_environment(env_id)
        if not env:
            return False

        self.db.delete(env)
        self.db.commit()

        logger.info(f"Deleted environment: {env.name}")
        return True

    # =========================================================================
    # Environment Operations
    # =========================================================================

    def get_env_vars(self, env_id: int) -> Dict[str, str]:
        """
        Get environment variables for an environment

        Args:
            env_id: Environment ID

        Returns:
            Dict of environment variables
        """
        env = self.get_environment(env_id)
        if not env or not env.env_vars_json:
            return {}

        try:
            return json.loads(env.env_vars_json)
        except json.JSONDecodeError:
            return {}

    def set_env_vars(self, env_id: int, env_vars: Dict[str, str]) -> bool:
        """
        Set environment variables

        Args:
            env_id: Environment ID
            env_vars: Dict of environment variables

        Returns:
            True if successful
        """
        env = self.get_environment(env_id)
        if not env:
            return False

        env.env_vars_json = json.dumps(env_vars)
        env.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def get_next_environment(self, env_id: int) -> Optional[Environment]:
        """
        Get the next environment in the promotion chain

        Args:
            env_id: Current environment ID

        Returns:
            Next environment or None if at the end
        """
        current = self.get_environment(env_id)
        if not current:
            return None

        return self.db.query(Environment).filter(
            Environment.project_id == current.project_id,
            Environment.order > current.order,
            Environment.is_active == True
        ).order_by(Environment.order).first()

    def find_environment_by_branch(self, project_id: int, branch: str) -> Optional[Environment]:
        """
        Find an environment configured for auto-deploy on a specific branch

        Args:
            project_id: Project ID
            branch: Git branch name

        Returns:
            Environment configured for auto-deploy on this branch, or None
        """
        return self.db.query(Environment).filter(
            Environment.project_id == project_id,
            Environment.branch == branch,
            Environment.auto_deploy == True,
            Environment.is_active == True
        ).first()

    def approve_environment(self, env_id: int, approved_by: str) -> bool:
        """
        Record approval for an environment that requires it

        Args:
            env_id: Environment ID
            approved_by: Username of approver

        Returns:
            True if successful
        """
        env = self.get_environment(env_id)
        if not env:
            return False

        env.approved_by = approved_by
        env.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Environment {env.name} approved by {approved_by}")
        return True

    async def test_connection(self, env_id: int) -> Dict[str, Any]:
        """
        Test connection to an environment's Docker host

        Args:
            env_id: Environment ID

        Returns:
            Dict with success status and info/error
        """
        env = self.get_environment(env_id)
        if not env:
            return {"success": False, "error": "Environment not found"}

        if not env.docker_host:
            return {"success": False, "error": "No Docker host configured"}

        try:
            # Import Docker service
            try:
                from .docker_service import DockerService
            except ImportError:
                from docker_service import DockerService

            docker = DockerService(docker_host=env.docker_host)
            info = docker.client.info()

            return {
                "success": True,
                "docker_version": info.get("ServerVersion"),
                "containers": info.get("Containers"),
                "images": info.get("Images"),
                "os": info.get("OperatingSystem")
            }

        except Exception as e:
            logger.error(f"Failed to connect to environment {env.name}: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Default Environments
    # =========================================================================

    def create_default_environments(self, project_id: int) -> List[Environment]:
        """
        Create default environments for a new project

        Args:
            project_id: Project ID

        Returns:
            List of created environments
        """
        defaults = [
            {
                "name": "development",
                "display_name": "Development",
                "order": 1,
                "branch": "develop",
                "auto_deploy": True,
                "requires_approval": False
            },
            {
                "name": "staging",
                "display_name": "Staging",
                "order": 2,
                "branch": "staging",
                "auto_deploy": True,
                "requires_approval": False
            },
            {
                "name": "production",
                "display_name": "Production",
                "order": 3,
                "branch": "main",
                "auto_deploy": False,
                "requires_approval": True
            }
        ]

        environments = []
        for env_data in defaults:
            env = self.create_environment(project_id, env_data)
            environments.append(env)

        logger.info(f"Created default environments for project {project_id}")
        return environments


# Singleton instance
_env_service = None


def get_environment_service(db: Session = None) -> EnvironmentService:
    """Get environment service instance"""
    if db:
        return EnvironmentService(db)

    global _env_service
    if _env_service is None:
        _env_service = EnvironmentService()
    return _env_service
