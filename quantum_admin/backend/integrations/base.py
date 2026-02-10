"""
Base Cloud Connector Interface
Abstract base class for cloud provider integrations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    KUBERNETES = "kubernetes"
    AZURE = "azure"
    GCP = "gcp"


class DeploymentStatus(str, Enum):
    """Deployment status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentResult:
    """Result of a deployment operation."""
    success: bool
    deployment_id: str
    status: DeploymentStatus
    message: str = ""
    url: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "status": self.status.value,
            "message": self.message,
            "url": self.url,
            "logs": self.logs,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ResourceInfo:
    """Information about a cloud resource."""
    id: str
    name: str
    type: str
    status: str
    region: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "status": self.status,
            "region": self.region,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.metadata
        }


class CloudConnector(ABC):
    """
    Abstract base class for cloud provider connectors.
    All cloud integrations must implement this interface.
    """

    def __init__(self, credentials: Dict[str, Any]):
        """
        Initialize the connector with credentials.

        Args:
            credentials: Provider-specific credentials dictionary
        """
        self.credentials = credentials
        self._client = None

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """Return the cloud provider type."""
        pass

    @property
    @abstractmethod
    def required_credentials(self) -> List[str]:
        """Return list of required credential fields."""
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that the provided credentials are correct.

        Returns:
            True if credentials are valid, False otherwise
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the cloud provider.

        Returns:
            Dict with connection status and details
        """
        pass

    @abstractmethod
    def deploy(
        self,
        image: str,
        config: Dict[str, Any],
        environment: str = "production"
    ) -> DeploymentResult:
        """
        Deploy an application to the cloud provider.

        Args:
            image: Docker image to deploy
            config: Deployment configuration
            environment: Target environment name

        Returns:
            DeploymentResult with deployment status
        """
        pass

    @abstractmethod
    def get_deployment_status(self, deployment_id: str) -> DeploymentResult:
        """
        Get the status of a deployment.

        Args:
            deployment_id: ID of the deployment

        Returns:
            DeploymentResult with current status
        """
        pass

    @abstractmethod
    def rollback(self, deployment_id: str, target_version: str = None) -> DeploymentResult:
        """
        Rollback a deployment to a previous version.

        Args:
            deployment_id: ID of the deployment to rollback
            target_version: Specific version to rollback to (optional)

        Returns:
            DeploymentResult with rollback status
        """
        pass

    @abstractmethod
    def get_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """
        Get logs for a deployment.

        Args:
            deployment_id: ID of the deployment
            lines: Number of log lines to retrieve

        Returns:
            List of log lines
        """
        pass

    @abstractmethod
    def list_resources(self, resource_type: str = None) -> List[ResourceInfo]:
        """
        List resources in the cloud provider.

        Args:
            resource_type: Filter by resource type (optional)

        Returns:
            List of ResourceInfo objects
        """
        pass

    @abstractmethod
    def delete_deployment(self, deployment_id: str) -> bool:
        """
        Delete a deployment.

        Args:
            deployment_id: ID of the deployment to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get the JSON schema for deployment configuration.
        Override in subclasses for provider-specific options.

        Returns:
            JSON Schema for configuration
        """
        return {
            "type": "object",
            "properties": {
                "replicas": {"type": "integer", "default": 1},
                "cpu": {"type": "string", "default": "0.5"},
                "memory": {"type": "string", "default": "512Mi"},
                "port": {"type": "integer", "default": 8080},
                "env_vars": {
                    "type": "object",
                    "additionalProperties": {"type": "string"}
                }
            }
        }

    def get_regions(self) -> List[Dict[str, str]]:
        """
        Get available regions for deployment.
        Override in subclasses.

        Returns:
            List of region dictionaries with id and name
        """
        return []

    def _mask_credentials(self, creds: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive credential values for logging."""
        masked = {}
        for key, value in creds.items():
            if isinstance(value, str) and len(value) > 8:
                masked[key] = value[:4] + "****" + value[-4:]
            else:
                masked[key] = "****"
        return masked
