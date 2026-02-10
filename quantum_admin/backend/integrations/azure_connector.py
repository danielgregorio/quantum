"""
Azure Connector for Quantum Admin
Supports Azure Container Instances and Azure Kubernetes Service
"""

import logging
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


class AzureConnector(CloudConnector):
    """
    Azure Cloud Connector.
    Supports deployment to Azure Container Instances (ACI) and AKS.
    """

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AZURE

    @property
    def required_credentials(self) -> List[str]:
        return ["subscription_id", "tenant_id", "client_id", "client_secret"]

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._container_client = None
        self._resource_client = None

    def _get_azure_clients(self):
        """Initialize Azure clients lazily."""
        if self._container_client is None:
            try:
                from azure.identity import ClientSecretCredential
                from azure.mgmt.containerinstance import ContainerInstanceManagementClient
                from azure.mgmt.resource import ResourceManagementClient

                credential = ClientSecretCredential(
                    tenant_id=self.credentials.get("tenant_id"),
                    client_id=self.credentials.get("client_id"),
                    client_secret=self.credentials.get("client_secret")
                )

                subscription_id = self.credentials.get("subscription_id")

                self._container_client = ContainerInstanceManagementClient(
                    credential,
                    subscription_id
                )
                self._resource_client = ResourceManagementClient(
                    credential,
                    subscription_id
                )

            except ImportError:
                logger.warning("Azure SDK not installed (azure-mgmt-containerinstance)")
                return False
            except Exception as e:
                logger.error(f"Failed to create Azure clients: {e}")
                return False
        return True

    def validate_credentials(self) -> bool:
        """Validate Azure credentials."""
        required = self.required_credentials
        for field in required:
            if not self.credentials.get(field):
                return False
        return True

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Azure."""
        if not self.validate_credentials():
            return {
                "success": False,
                "error": "Missing required credentials",
                "required": self.required_credentials
            }

        if not self._get_azure_clients():
            return {
                "success": False,
                "error": "Could not initialize Azure clients. Is azure-mgmt-containerinstance installed?"
            }

        try:
            # List resource groups as connection test
            groups = list(self._resource_client.resource_groups.list())
            return {
                "success": True,
                "message": "Connected to Azure successfully",
                "subscription_id": self.credentials.get("subscription_id"),
                "resource_groups": len(groups)
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
        """Deploy to Azure Container Instances."""
        if not self._get_azure_clients():
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message="Could not initialize Azure clients"
            )

        try:
            from azure.mgmt.containerinstance.models import (
                ContainerGroup,
                Container,
                ContainerPort,
                ResourceRequests,
                ResourceRequirements,
                IpAddress,
                Port,
                OperatingSystemTypes,
                EnvironmentVariable
            )

            resource_group = config.get("resource_group", "quantum-rg")
            container_name = config.get("container_name", f"quantum-{environment}")
            location = config.get("location", "eastus")
            cpu = float(config.get("cpu", "1.0"))
            memory = float(config.get("memory", "1.5"))
            port = config.get("port", 8080)

            # Ensure resource group exists
            if not self._resource_client.resource_groups.check_existence(resource_group):
                self._resource_client.resource_groups.create_or_update(
                    resource_group,
                    {"location": location}
                )

            # Create container group
            container_group = ContainerGroup(
                location=location,
                containers=[
                    Container(
                        name=container_name,
                        image=image,
                        resources=ResourceRequirements(
                            requests=ResourceRequests(cpu=cpu, memory_in_gb=memory)
                        ),
                        ports=[ContainerPort(port=port)],
                        environment_variables=[
                            EnvironmentVariable(name=k, value=v)
                            for k, v in config.get("env_vars", {}).items()
                        ]
                    )
                ],
                os_type=OperatingSystemTypes.linux,
                ip_address=IpAddress(
                    type="Public",
                    ports=[Port(protocol="TCP", port=port)],
                    dns_name_label=config.get("dns_label", container_name)
                ),
                restart_policy="Always"
            )

            # Deploy container group
            result = self._container_client.container_groups.begin_create_or_update(
                resource_group,
                container_name,
                container_group
            ).result()

            deployment_id = f"{resource_group}/{container_name}"

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.IN_PROGRESS,
                message=f"Deployment started for {container_name}",
                url=f"http://{result.ip_address.fqdn}:{port}" if result.ip_address else None,
                metadata={
                    "resource_group": resource_group,
                    "location": location,
                    "image": image
                }
            )

        except Exception as e:
            logger.error(f"Azure deployment failed: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_deployment_status(self, deployment_id: str) -> DeploymentResult:
        """Get status of an Azure Container Instance deployment."""
        if not self._get_azure_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize Azure clients"
            )

        try:
            parts = deployment_id.split("/")
            resource_group = parts[0]
            container_name = parts[1]

            container_group = self._container_client.container_groups.get(
                resource_group,
                container_name
            )

            state = container_group.containers[0].instance_view.current_state.state if \
                container_group.containers[0].instance_view else "Unknown"

            if state == "Running":
                status = DeploymentStatus.SUCCEEDED
            elif state in ("Waiting", "Starting"):
                status = DeploymentStatus.IN_PROGRESS
            else:
                status = DeploymentStatus.FAILED

            return DeploymentResult(
                success=status == DeploymentStatus.SUCCEEDED,
                deployment_id=deployment_id,
                status=status,
                message=f"Container state: {state}",
                url=f"http://{container_group.ip_address.fqdn}" if container_group.ip_address else None,
                metadata={
                    "state": state,
                    "provisioning_state": container_group.provisioning_state
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
        """Rollback is not directly supported for ACI. Redeploy with previous image."""
        return DeploymentResult(
            success=False,
            deployment_id=deployment_id,
            status=DeploymentStatus.FAILED,
            message="Azure Container Instances does not support rollback. Redeploy with previous image version."
        )

    def get_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get container logs."""
        if not self._get_azure_clients():
            return ["Error: Could not initialize Azure clients"]

        try:
            parts = deployment_id.split("/")
            resource_group = parts[0]
            container_name = parts[1]

            logs = self._container_client.containers.list_logs(
                resource_group,
                container_name,
                container_name,
                tail=lines
            )

            return logs.content.split("\n") if logs.content else []

        except Exception as e:
            return [f"Error getting logs: {e}"]

    def list_resources(self, resource_type: str = None) -> List[ResourceInfo]:
        """List Azure Container Instances."""
        if not self._get_azure_clients():
            return []

        resources = []

        try:
            container_groups = self._container_client.container_groups.list()

            for cg in container_groups:
                state = "unknown"
                if cg.containers and cg.containers[0].instance_view:
                    state = cg.containers[0].instance_view.current_state.state

                resources.append(ResourceInfo(
                    id=cg.id,
                    name=cg.name,
                    type="container_group",
                    status=state.lower() if state else "unknown",
                    region=cg.location,
                    created_at=None,
                    metadata={
                        "provisioning_state": cg.provisioning_state,
                        "ip_address": cg.ip_address.ip if cg.ip_address else None,
                        "os_type": cg.os_type
                    }
                ))

        except Exception as e:
            logger.error(f"Error listing Azure resources: {e}")

        return resources

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete an Azure Container Instance."""
        if not self._get_azure_clients():
            return False

        try:
            parts = deployment_id.split("/")
            resource_group = parts[0]
            container_name = parts[1]

            self._container_client.container_groups.begin_delete(
                resource_group,
                container_name
            ).result()

            return True

        except Exception as e:
            logger.error(f"Error deleting deployment: {e}")
            return False

    def get_regions(self) -> List[Dict[str, str]]:
        """Get available Azure regions."""
        return [
            {"id": "eastus", "name": "East US"},
            {"id": "eastus2", "name": "East US 2"},
            {"id": "westus", "name": "West US"},
            {"id": "westus2", "name": "West US 2"},
            {"id": "centralus", "name": "Central US"},
            {"id": "northeurope", "name": "North Europe"},
            {"id": "westeurope", "name": "West Europe"},
            {"id": "uksouth", "name": "UK South"},
            {"id": "ukwest", "name": "UK West"},
            {"id": "southeastasia", "name": "Southeast Asia"},
            {"id": "eastasia", "name": "East Asia"},
            {"id": "japaneast", "name": "Japan East"},
            {"id": "australiaeast", "name": "Australia East"},
            {"id": "brazilsouth", "name": "Brazil South"},
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get Azure-specific deployment configuration schema."""
        schema = super().get_config_schema()
        schema["properties"].update({
            "resource_group": {"type": "string", "default": "quantum-rg"},
            "container_name": {"type": "string"},
            "location": {"type": "string", "default": "eastus"},
            "dns_label": {"type": "string"},
            "restart_policy": {
                "type": "string",
                "enum": ["Always", "OnFailure", "Never"],
                "default": "Always"
            }
        })
        return schema
