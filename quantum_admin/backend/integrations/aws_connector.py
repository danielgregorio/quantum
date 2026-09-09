"""
AWS Connector for Quantum Admin
Supports ECS, EKS, and Lambda deployments
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


class AWSConnector(CloudConnector):
    """
    AWS Cloud Connector.
    Supports deployment to ECS Fargate, EKS, and Lambda.
    """

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.AWS

    @property
    def required_credentials(self) -> List[str]:
        return ["access_key_id", "secret_access_key", "region"]

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._ecs_client = None
        self._ec2_client = None
        self._logs_client = None

    def _get_boto_clients(self):
        """Initialize boto3 clients lazily."""
        if self._ecs_client is None:
            try:
                import boto3
                session = boto3.Session(
                    aws_access_key_id=self.credentials.get("access_key_id"),
                    aws_secret_access_key=self.credentials.get("secret_access_key"),
                    region_name=self.credentials.get("region", "us-east-1")
                )
                self._ecs_client = session.client("ecs")
                self._ec2_client = session.client("ec2")
                self._logs_client = session.client("logs")
            except ImportError:
                logger.warning("boto3 not installed")
                return False
            except Exception as e:
                logger.error(f"Failed to create AWS clients: {e}")
                return False
        return True

    def validate_credentials(self) -> bool:
        """Validate AWS credentials."""
        required = self.required_credentials
        for field in required:
            if not self.credentials.get(field):
                return False
        return True

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to AWS."""
        if not self.validate_credentials():
            return {
                "success": False,
                "error": "Missing required credentials",
                "required": self.required_credentials
            }

        if not self._get_boto_clients():
            return {
                "success": False,
                "error": "Could not initialize AWS clients. Is boto3 installed?"
            }

        try:
            # Try to list ECS clusters as a connection test
            response = self._ecs_client.list_clusters()
            return {
                "success": True,
                "message": "Connected to AWS successfully",
                "region": self.credentials.get("region"),
                "clusters": len(response.get("clusterArns", []))
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
        """Deploy to AWS ECS Fargate."""
        if not self._get_boto_clients():
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message="Could not initialize AWS clients"
            )

        try:
            cluster = config.get("cluster", "quantum-cluster")
            service_name = config.get("service_name", f"quantum-{environment}")
            task_family = config.get("task_family", f"quantum-{environment}-task")
            cpu = config.get("cpu", "256")
            memory = config.get("memory", "512")
            port = config.get("port", 8080)

            # Register task definition
            task_def = self._ecs_client.register_task_definition(
                family=task_family,
                networkMode="awsvpc",
                requiresCompatibilities=["FARGATE"],
                cpu=cpu,
                memory=memory,
                containerDefinitions=[
                    {
                        "name": service_name,
                        "image": image,
                        "portMappings": [
                            {"containerPort": port, "protocol": "tcp"}
                        ],
                        "environment": [
                            {"name": k, "value": v}
                            for k, v in config.get("env_vars", {}).items()
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": f"/ecs/{service_name}",
                                "awslogs-region": self.credentials.get("region"),
                                "awslogs-stream-prefix": "ecs"
                            }
                        }
                    }
                ]
            )

            task_def_arn = task_def["taskDefinition"]["taskDefinitionArn"]

            # Update or create service
            try:
                self._ecs_client.update_service(
                    cluster=cluster,
                    service=service_name,
                    taskDefinition=task_def_arn,
                    desiredCount=config.get("replicas", 1),
                    forceNewDeployment=True
                )
                deployment_id = f"{cluster}/{service_name}"
            except self._ecs_client.exceptions.ServiceNotFoundException:
                # Create new service
                self._ecs_client.create_service(
                    cluster=cluster,
                    serviceName=service_name,
                    taskDefinition=task_def_arn,
                    desiredCount=config.get("replicas", 1),
                    launchType="FARGATE",
                    networkConfiguration={
                        "awsvpcConfiguration": {
                            "subnets": config.get("subnets", []),
                            "securityGroups": config.get("security_groups", []),
                            "assignPublicIp": "ENABLED"
                        }
                    }
                )
                deployment_id = f"{cluster}/{service_name}"

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.IN_PROGRESS,
                message=f"Deployment started for {service_name}",
                metadata={
                    "task_definition": task_def_arn,
                    "cluster": cluster,
                    "image": image
                }
            )

        except Exception as e:
            logger.error(f"AWS deployment failed: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_deployment_status(self, deployment_id: str) -> DeploymentResult:
        """Get status of an ECS deployment."""
        if not self._get_boto_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize AWS clients"
            )

        try:
            parts = deployment_id.split("/")
            cluster = parts[0]
            service_name = parts[1]

            response = self._ecs_client.describe_services(
                cluster=cluster,
                services=[service_name]
            )

            if not response.get("services"):
                return DeploymentResult(
                    success=False,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="Service not found"
                )

            service = response["services"][0]
            running_count = service.get("runningCount", 0)
            desired_count = service.get("desiredCount", 1)

            if running_count >= desired_count:
                status = DeploymentStatus.SUCCEEDED
            elif service.get("status") == "ACTIVE":
                status = DeploymentStatus.IN_PROGRESS
            else:
                status = DeploymentStatus.FAILED

            return DeploymentResult(
                success=status == DeploymentStatus.SUCCEEDED,
                deployment_id=deployment_id,
                status=status,
                message=f"Running {running_count}/{desired_count} tasks",
                metadata={
                    "service_status": service.get("status"),
                    "running_count": running_count,
                    "desired_count": desired_count
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
        """Rollback to a previous task definition."""
        if not self._get_boto_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize AWS clients"
            )

        try:
            parts = deployment_id.split("/")
            cluster = parts[0]
            service_name = parts[1]

            # Get service to find task definition
            response = self._ecs_client.describe_services(
                cluster=cluster,
                services=[service_name]
            )

            if not response.get("services"):
                return DeploymentResult(
                    success=False,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="Service not found"
                )

            service = response["services"][0]
            current_task_def = service.get("taskDefinition", "")

            # Find previous task definition
            family = current_task_def.split("/")[-1].split(":")[0]
            task_defs = self._ecs_client.list_task_definitions(
                familyPrefix=family,
                sort="DESC",
                maxResults=10
            )

            if len(task_defs.get("taskDefinitionArns", [])) < 2:
                return DeploymentResult(
                    success=False,
                    deployment_id=deployment_id,
                    status=DeploymentStatus.FAILED,
                    message="No previous version to rollback to"
                )

            # Use target_version or previous version
            if target_version:
                target_arn = f"{family}:{target_version}"
            else:
                target_arn = task_defs["taskDefinitionArns"][1]

            # Update service to previous task definition
            self._ecs_client.update_service(
                cluster=cluster,
                service=service_name,
                taskDefinition=target_arn,
                forceNewDeployment=True
            )

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.ROLLING_BACK,
                message=f"Rolling back to {target_arn}",
                metadata={"target_task_definition": target_arn}
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get CloudWatch logs for the service."""
        if not self._get_boto_clients():
            return [f"Error: Could not initialize AWS clients"]

        try:
            parts = deployment_id.split("/")
            service_name = parts[1] if len(parts) > 1 else deployment_id

            log_group = f"/ecs/{service_name}"

            response = self._logs_client.filter_log_events(
                logGroupName=log_group,
                limit=lines,
                interleaved=True
            )

            logs = []
            for event in response.get("events", []):
                timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
                logs.append(f"[{timestamp}] {event['message']}")

            return logs

        except Exception as e:
            return [f"Error getting logs: {e}"]

    def list_resources(self, resource_type: str = None) -> List[ResourceInfo]:
        """List AWS resources (ECS services, tasks)."""
        if not self._get_boto_clients():
            return []

        resources = []

        try:
            # List ECS clusters and services
            clusters = self._ecs_client.list_clusters()

            for cluster_arn in clusters.get("clusterArns", []):
                cluster_name = cluster_arn.split("/")[-1]

                services = self._ecs_client.list_services(cluster=cluster_name)
                for service_arn in services.get("serviceArns", []):
                    service_name = service_arn.split("/")[-1]
                    resources.append(ResourceInfo(
                        id=service_arn,
                        name=service_name,
                        type="ecs_service",
                        status="active",
                        region=self.credentials.get("region"),
                        metadata={"cluster": cluster_name}
                    ))

        except Exception as e:
            logger.error(f"Error listing AWS resources: {e}")

        return resources

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete an ECS service."""
        if not self._get_boto_clients():
            return False

        try:
            parts = deployment_id.split("/")
            cluster = parts[0]
            service_name = parts[1]

            # Scale down to 0 first
            self._ecs_client.update_service(
                cluster=cluster,
                service=service_name,
                desiredCount=0
            )

            # Delete service
            self._ecs_client.delete_service(
                cluster=cluster,
                service=service_name
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting deployment: {e}")
            return False

    def get_regions(self) -> List[Dict[str, str]]:
        """Get available AWS regions."""
        return [
            {"id": "us-east-1", "name": "US East (N. Virginia)"},
            {"id": "us-east-2", "name": "US East (Ohio)"},
            {"id": "us-west-1", "name": "US West (N. California)"},
            {"id": "us-west-2", "name": "US West (Oregon)"},
            {"id": "eu-west-1", "name": "Europe (Ireland)"},
            {"id": "eu-west-2", "name": "Europe (London)"},
            {"id": "eu-central-1", "name": "Europe (Frankfurt)"},
            {"id": "ap-southeast-1", "name": "Asia Pacific (Singapore)"},
            {"id": "ap-southeast-2", "name": "Asia Pacific (Sydney)"},
            {"id": "ap-northeast-1", "name": "Asia Pacific (Tokyo)"},
            {"id": "sa-east-1", "name": "South America (Sao Paulo)"},
        ]

    def get_config_schema(self) -> Dict[str, Any]:
        """Get AWS-specific deployment configuration schema."""
        schema = super().get_config_schema()
        schema["properties"].update({
            "cluster": {"type": "string", "default": "quantum-cluster"},
            "service_name": {"type": "string"},
            "task_family": {"type": "string"},
            "subnets": {"type": "array", "items": {"type": "string"}},
            "security_groups": {"type": "array", "items": {"type": "string"}},
            "launch_type": {
                "type": "string",
                "enum": ["FARGATE", "EC2"],
                "default": "FARGATE"
            }
        })
        return schema
