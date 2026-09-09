"""
GCP Connector for Quantum Admin
Supports Google Cloud Run and Google Kubernetes Engine
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import (
    CloudConnector,
    CloudProvider,
    DeploymentResult,
    DeploymentStatus,
    ResourceInfo
)

logger = logging.getLogger(__name__)


class GCPConnector(CloudConnector):
    """
    Google Cloud Platform Connector.
    Supports deployment to Cloud Run and GKE.
    """

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.GCP

    @property
    def required_credentials(self) -> List[str]:
        return ["project_id", "service_account_json"]

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._run_client = None
        self._gke_client = None

    def _get_gcp_clients(self):
        """Initialize GCP clients lazily."""
        if self._run_client is None:
            try:
                from google.cloud import run_v2
                from google.oauth2 import service_account

                # Parse service account JSON
                sa_json = self.credentials.get("service_account_json")
                if isinstance(sa_json, str):
                    sa_info = json.loads(sa_json)
                else:
                    sa_info = sa_json

                creds = service_account.Credentials.from_service_account_info(sa_info)

                self._run_client = run_v2.ServicesClient(credentials=creds)

            except ImportError:
                logger.warning("Google Cloud SDK not installed (google-cloud-run)")
                return False
            except Exception as e:
                logger.error(f"Failed to create GCP clients: {e}")
                return False
        return True

    def validate_credentials(self) -> bool:
        """Validate GCP credentials."""
        if not self.credentials.get("project_id"):
            return False
        if not self.credentials.get("service_account_json"):
            return False
        return True

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to GCP."""
        if not self.validate_credentials():
            return {
                "success": False,
                "error": "Missing required credentials",
                "required": self.required_credentials
            }

        if not self._get_gcp_clients():
            return {
                "success": False,
                "error": "Could not initialize GCP clients. Is google-cloud-run installed?"
            }

        try:
            project_id = self.credentials.get("project_id")
            region = self.credentials.get("region", "us-central1")

            # List Cloud Run services as connection test
            parent = f"projects/{project_id}/locations/{region}"
            services = list(self._run_client.list_services(parent=parent))

            return {
                "success": True,
                "message": "Connected to GCP successfully",
                "project_id": project_id,
                "region": region,
                "services": len(services)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def deploy(
        self,
        image: str,
        config: Dict[str, Any],
        environment: str = "production"
    ) -> DeploymentResult:
        """Deploy to Google Cloud Run."""
        if not self._get_gcp_clients():
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message="Could not initialize GCP clients"
            )

        try:
            from google.cloud import run_v2

            project_id = self.credentials.get("project_id")
            region = config.get("region", self.credentials.get("region", "us-central1"))
            service_name = config.get("service_name", f"quantum-{environment}")
            cpu = config.get("cpu", "1")
            memory = config.get("memory", "512Mi")
            port = config.get("port", 8080)
            min_instances = config.get("min_instances", 0)
            max_instances = config.get("max_instances", 100)

            parent = f"projects/{project_id}/locations/{region}"

            # Build service definition
            service = run_v2.Service(
                template=run_v2.RevisionTemplate(
                    containers=[
                        run_v2.Container(
                            image=image,
                            ports=[run_v2.ContainerPort(container_port=port)],
                            resources=run_v2.ResourceRequirements(
                                limits={"cpu": cpu, "memory": memory}
                            ),
                            env=[
                                run_v2.EnvVar(name=k, value=v)
                                for k, v in config.get("env_vars", {}).items()
                            ]
                        )
                    ],
                    scaling=run_v2.RevisionScaling(
                        min_instance_count=min_instances,
                        max_instance_count=max_instances
                    )
                )
            )

            # Create or update service
            try:
                existing = self._run_client.get_service(
                    name=f"{parent}/services/{service_name}"
                )
                # Update
                service.name = existing.name
                operation = self._run_client.update_service(service=service)
                action = "updated"
            except Exception:
                # Create
                operation = self._run_client.create_service(
                    parent=parent,
                    service=service,
                    service_id=service_name
                )
                action = "created"

            result = operation.result()
            deployment_id = f"{project_id}/{region}/{service_name}"

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.IN_PROGRESS,
                message=f"Service {action} for {service_name}",
                url=result.uri if hasattr(result, 'uri') else None,
                metadata={
                    "project_id": project_id,
                    "region": region,
                    "image": image
                }
            )

        except Exception as e:
            logger.error(f"GCP deployment failed: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_deployment_status(self, deployment_id: str) -> DeploymentResult:
        """Get status of a Cloud Run deployment."""
        if not self._get_gcp_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize GCP clients"
            )

        try:
            parts = deployment_id.split("/")
            project_id = parts[0]
            region = parts[1]
            service_name = parts[2]

            name = f"projects/{project_id}/locations/{region}/services/{service_name}"
            service = self._run_client.get_service(name=name)

            # Check conditions
            is_ready = False
            for condition in service.conditions:
                if condition.type == "Ready" and condition.state == "CONDITION_SUCCEEDED":
                    is_ready = True
                    break

            if is_ready:
                status = DeploymentStatus.SUCCEEDED
            else:
                status = DeploymentStatus.IN_PROGRESS

            return DeploymentResult(
                success=is_ready,
                deployment_id=deployment_id,
                status=status,
                message=f"Service {'ready' if is_ready else 'deploying'}",
                url=service.uri if hasattr(service, 'uri') else None,
                metadata={
                    "latest_revision": service.latest_ready_revision if hasattr(service, 'latest_ready_revision') else None,
                    "traffic": [
                        {"revision": t.revision, "percent": t.percent}
                        for t in service.traffic
                    ] if hasattr(service, 'traffic') else []
                }
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def rollback(self, deployment_id: str, target_version: str = None) -> DeploymentResult:
        """Rollback to a previous revision."""
        if not self._get_gcp_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize GCP clients"
            )

        try:
            from google.cloud import run_v2

            parts = deployment_id.split("/")
            project_id = parts[0]
            region = parts[1]
            service_name = parts[2]

            name = f"projects/{project_id}/locations/{region}/services/{service_name}"
            service = self._run_client.get_service(name=name)

            if not target_version:
                # Find previous revision from traffic
                if len(service.traffic) > 1:
                    target_version = service.traffic[1].revision
                else:
                    return DeploymentResult(
                        success=False,
                        deployment_id=deployment_id,
                        status=DeploymentStatus.FAILED,
                        message="No previous revision to rollback to"
                    )

            # Update traffic to route to target revision
            service.traffic = [
                run_v2.TrafficTarget(
                    type=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION,
                    revision=target_version,
                    percent=100
                )
            ]

            operation = self._run_client.update_service(service=service)
            operation.result()

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.ROLLING_BACK,
                message=f"Traffic routed to revision {target_version}",
                metadata={"target_revision": target_version}
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get Cloud Run logs via Cloud Logging."""
        try:
            from google.cloud import logging as cloud_logging
            from google.oauth2 import service_account
            import json

            sa_json = self.credentials.get("service_account_json")
            if isinstance(sa_json, str):
                sa_info = json.loads(sa_json)
            else:
                sa_info = sa_json

            creds = service_account.Credentials.from_service_account_info(sa_info)
            client = cloud_logging.Client(
                project=self.credentials.get("project_id"),
                credentials=creds
            )

            parts = deployment_id.split("/")
            service_name = parts[2] if len(parts) > 2 else deployment_id

            # Query logs
            filter_str = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"'
            entries = client.list_entries(filter_=filter_str, max_results=lines)

            logs = []
            for entry in entries:
                timestamp = entry.timestamp.isoformat() if entry.timestamp else ""
                payload = entry.payload if hasattr(entry, 'payload') else str(entry)
                logs.append(f"[{timestamp}] {payload}")

            return logs

        except Exception as e:
            return [f"Error getting logs: {e}"]

    def list_resources(self, resource_type: str = None) -> List[ResourceInfo]:
        """List Cloud Run services."""
        if not self._get_gcp_clients():
            return []

        resources = []

        try:
            project_id = self.credentials.get("project_id")
            region = self.credentials.get("region", "us-central1")
            parent = f"projects/{project_id}/locations/{region}"

            services = self._run_client.list_services(parent=parent)

            for service in services:
                is_ready = False
                for condition in service.conditions:
                    if condition.type == "Ready" and condition.state == "CONDITION_SUCCEEDED":
                        is_ready = True
                        break

                resources.append(ResourceInfo(
                    id=service.name,
                    name=service.name.split("/")[-1],
                    type="cloud_run_service",
                    status="running" if is_ready else "deploying",
                    region=region,
                    created_at=service.create_time.timestamp() if hasattr(service, 'create_time') else None,
                    metadata={
                        "uri": service.uri if hasattr(service, 'uri') else None,
                        "latest_revision": service.latest_ready_revision if hasattr(service, 'latest_ready_revision') else None
                    }
                ))

        except Exception as e:
            logger.error(f"Error listing GCP resources: {e}")

        return resources

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a Cloud Run service."""
        if not self._get_gcp_clients():
            return False

        try:
            parts = deployment_id.split("/")
            project_id = parts[0]
            region = parts[1]
            service_name = parts[2]

            name = f"projects/{project_id}/locations/{region}/services/{service_name}"
            operation = self._run_client.delete_service(name=name)
            operation.result()

            return True

        except Exception as e:
            logger.error(f"Error deleting deployment: {e}")
            return False

    def get_regions(self) -> List[Dict[str, str]]:
        """Get available GCP regions for Cloud Run."""
        return [
            {"id": "us-central1", "name": "Iowa"},
            {"id": "us-east1", "name": "South Carolina"},
            {"id": "us-east4", "name": "Northern Virginia"},
            {"id": "us-west1", "name": "Oregon"},
            {"id": "us-west2", "name": "Los Angeles"},
            {"id": "us-west3", "name": "Salt Lake City"},
            {"id": "us-west4", "name": "Las Vegas"},
            {"id": "europe-west1", "name": "Belgium"},
            {"id": "europe-west2", "name": "London"},
            {"id": "europe-west3", "name": "Frankfurt"},
            {"id": "europe-west4", "name": "Netherlands"},
            {"id": "europe-north1", "name": "Finland"},
            {"id": "asia-east1", "name": "Taiwan"},
            {"id": "asia-northeast1", "name": "Tokyo"},
            {"id": "asia-southeast1", "name": "Singapore"},
            {"id": "australia-southeast1", "name": "Sydney"},
            {"id": "southamerica-east1", "name": "Sao Paulo"},
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get GCP-specific deployment configuration schema."""
        schema = super().get_config_schema()
        schema["properties"].update({
            "service_name": {"type": "string"},
            "region": {"type": "string", "default": "us-central1"},
            "min_instances": {"type": "integer", "default": 0},
            "max_instances": {"type": "integer", "default": 100},
            "allow_unauthenticated": {"type": "boolean", "default": True},
            "vpc_connector": {"type": "string"},
            "service_account": {"type": "string"}
        })
        return schema
