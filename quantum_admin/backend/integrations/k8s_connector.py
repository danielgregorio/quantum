"""
Kubernetes Connector for Quantum Admin
Supports deployment to any Kubernetes cluster
"""

import logging
import base64
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


class KubernetesConnector(CloudConnector):
    """
    Kubernetes Cloud Connector.
    Supports deployment to any K8s cluster via kubeconfig.
    """

    @property
    def provider(self) -> CloudProvider:
        return CloudProvider.KUBERNETES

    @property
    def required_credentials(self) -> List[str]:
        return ["kubeconfig"]  # or ["api_server", "token"]

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._api_client = None
        self._apps_v1 = None
        self._core_v1 = None

    def _get_k8s_clients(self):
        """Initialize Kubernetes clients lazily."""
        if self._api_client is None:
            try:
                from kubernetes import client, config

                # Load from kubeconfig string or file
                kubeconfig = self.credentials.get("kubeconfig")
                if kubeconfig:
                    import tempfile
                    import yaml

                    # If it's base64 encoded
                    try:
                        kubeconfig = base64.b64decode(kubeconfig).decode()
                    except Exception:
                        pass

                    # Write to temp file
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                        f.write(kubeconfig)
                        config.load_kube_config(f.name)
                elif self.credentials.get("api_server"):
                    # Use token-based auth
                    configuration = client.Configuration()
                    configuration.host = self.credentials.get("api_server")
                    configuration.api_key = {"authorization": f"Bearer {self.credentials.get('token')}"}
                    configuration.verify_ssl = self.credentials.get("verify_ssl", True)

                    if not configuration.verify_ssl and self.credentials.get("ca_cert"):
                        configuration.ssl_ca_cert = self.credentials.get("ca_cert")

                    client.Configuration.set_default(configuration)
                else:
                    # Try in-cluster config
                    config.load_incluster_config()

                self._api_client = client.ApiClient()
                self._apps_v1 = client.AppsV1Api()
                self._core_v1 = client.CoreV1Api()

            except ImportError:
                logger.warning("kubernetes package not installed")
                return False
            except Exception as e:
                logger.error(f"Failed to create K8s clients: {e}")
                return False
        return True

    def validate_credentials(self) -> bool:
        """Validate Kubernetes credentials."""
        if self.credentials.get("kubeconfig"):
            return True
        if self.credentials.get("api_server") and self.credentials.get("token"):
            return True
        return False

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Kubernetes cluster."""
        if not self.validate_credentials():
            return {
                "success": False,
                "error": "Missing required credentials",
                "required": ["kubeconfig or (api_server + token)"]
            }

        if not self._get_k8s_clients():
            return {
                "success": False,
                "error": "Could not initialize Kubernetes clients"
            }

        try:
            # List namespaces as connection test
            namespaces = self._core_v1.list_namespace()
            ns_names = [ns.metadata.name for ns in namespaces.items]

            return {
                "success": True,
                "message": "Connected to Kubernetes cluster",
                "namespaces": ns_names,
                "namespace_count": len(ns_names)
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
        """Deploy to Kubernetes."""
        if not self._get_k8s_clients():
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message="Could not initialize Kubernetes clients"
            )

        try:
            from kubernetes import client

            namespace = config.get("namespace", "default")
            app_name = config.get("app_name", f"quantum-{environment}")
            replicas = config.get("replicas", 1)
            port = config.get("port", 8080)
            cpu = config.get("cpu", "100m")
            memory = config.get("memory", "256Mi")

            # Create or update deployment
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=app_name,
                    namespace=namespace,
                    labels={"app": app_name, "environment": environment}
                ),
                spec=client.V1DeploymentSpec(
                    replicas=replicas,
                    selector=client.V1LabelSelector(
                        match_labels={"app": app_name}
                    ),
                    template=client.V1PodTemplateSpec(
                        metadata=client.V1ObjectMeta(
                            labels={"app": app_name, "environment": environment}
                        ),
                        spec=client.V1PodSpec(
                            containers=[
                                client.V1Container(
                                    name=app_name,
                                    image=image,
                                    ports=[client.V1ContainerPort(container_port=port)],
                                    resources=client.V1ResourceRequirements(
                                        requests={"cpu": cpu, "memory": memory},
                                        limits={"cpu": cpu, "memory": memory}
                                    ),
                                    env=[
                                        client.V1EnvVar(name=k, value=v)
                                        for k, v in config.get("env_vars", {}).items()
                                    ]
                                )
                            ]
                        )
                    )
                )
            )

            # Try to update existing deployment, create if not found
            try:
                self._apps_v1.replace_namespaced_deployment(
                    name=app_name,
                    namespace=namespace,
                    body=deployment
                )
                action = "updated"
            except Exception:
                self._apps_v1.create_namespaced_deployment(
                    namespace=namespace,
                    body=deployment
                )
                action = "created"

            deployment_id = f"{namespace}/{app_name}"

            # Create service if it doesn't exist
            try:
                self._core_v1.read_namespaced_service(name=app_name, namespace=namespace)
            except Exception:
                service = client.V1Service(
                    api_version="v1",
                    kind="Service",
                    metadata=client.V1ObjectMeta(name=app_name, namespace=namespace),
                    spec=client.V1ServiceSpec(
                        selector={"app": app_name},
                        ports=[client.V1ServicePort(port=port, target_port=port)],
                        type=config.get("service_type", "ClusterIP")
                    )
                )
                self._core_v1.create_namespaced_service(namespace=namespace, body=service)

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.IN_PROGRESS,
                message=f"Deployment {action} for {app_name}",
                metadata={
                    "namespace": namespace,
                    "image": image,
                    "replicas": replicas
                }
            )

        except Exception as e:
            logger.error(f"Kubernetes deployment failed: {e}")
            return DeploymentResult(
                success=False,
                deployment_id="",
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_deployment_status(self, deployment_id: str) -> DeploymentResult:
        """Get status of a Kubernetes deployment."""
        if not self._get_k8s_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize Kubernetes clients"
            )

        try:
            parts = deployment_id.split("/")
            namespace = parts[0] if len(parts) > 1 else "default"
            name = parts[-1]

            deployment = self._apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace
            )

            ready_replicas = deployment.status.ready_replicas or 0
            desired_replicas = deployment.spec.replicas or 1

            if ready_replicas >= desired_replicas:
                status = DeploymentStatus.SUCCEEDED
            elif deployment.status.conditions:
                for cond in deployment.status.conditions:
                    if cond.type == "Progressing" and cond.status == "True":
                        status = DeploymentStatus.IN_PROGRESS
                        break
                else:
                    status = DeploymentStatus.FAILED
            else:
                status = DeploymentStatus.IN_PROGRESS

            return DeploymentResult(
                success=status == DeploymentStatus.SUCCEEDED,
                deployment_id=deployment_id,
                status=status,
                message=f"Ready {ready_replicas}/{desired_replicas} replicas",
                metadata={
                    "ready_replicas": ready_replicas,
                    "desired_replicas": desired_replicas,
                    "generation": deployment.metadata.generation
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
        """Rollback to a previous deployment revision."""
        if not self._get_k8s_clients():
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message="Could not initialize Kubernetes clients"
            )

        try:
            from kubernetes import client

            parts = deployment_id.split("/")
            namespace = parts[0] if len(parts) > 1 else "default"
            name = parts[-1]

            # Get current deployment
            deployment = self._apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace
            )

            # Rollback by updating annotation to trigger a rollout
            if deployment.spec.template.metadata.annotations is None:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"] = \
                datetime.utcnow().isoformat()

            if target_version:
                # Set specific image version
                for container in deployment.spec.template.spec.containers:
                    image_parts = container.image.split(":")
                    container.image = f"{image_parts[0]}:{target_version}"

            self._apps_v1.replace_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=deployment
            )

            return DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                status=DeploymentStatus.ROLLING_BACK,
                message=f"Rollback initiated for {name}",
                metadata={"target_version": target_version}
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                status=DeploymentStatus.FAILED,
                message=str(e)
            )

    def get_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Get pod logs for a deployment."""
        if not self._get_k8s_clients():
            return ["Error: Could not initialize Kubernetes clients"]

        try:
            parts = deployment_id.split("/")
            namespace = parts[0] if len(parts) > 1 else "default"
            app_name = parts[-1]

            # Get pods for this deployment
            pods = self._core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={app_name}"
            )

            logs = []
            for pod in pods.items[:3]:  # Limit to 3 pods
                try:
                    pod_logs = self._core_v1.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=namespace,
                        tail_lines=lines // 3
                    )
                    for line in pod_logs.split("\n"):
                        logs.append(f"[{pod.metadata.name}] {line}")
                except Exception as e:
                    logs.append(f"[{pod.metadata.name}] Error: {e}")

            return logs

        except Exception as e:
            return [f"Error getting logs: {e}"]

    def list_resources(self, resource_type: str = None) -> List[ResourceInfo]:
        """List Kubernetes resources."""
        if not self._get_k8s_clients():
            return []

        resources = []

        try:
            # List deployments
            if resource_type in (None, "deployment"):
                deployments = self._apps_v1.list_deployment_for_all_namespaces()
                for dep in deployments.items:
                    resources.append(ResourceInfo(
                        id=f"{dep.metadata.namespace}/{dep.metadata.name}",
                        name=dep.metadata.name,
                        type="deployment",
                        status="running" if (dep.status.ready_replicas or 0) > 0 else "pending",
                        metadata={
                            "namespace": dep.metadata.namespace,
                            "replicas": dep.spec.replicas,
                            "ready_replicas": dep.status.ready_replicas
                        }
                    ))

            # List services
            if resource_type in (None, "service"):
                services = self._core_v1.list_service_for_all_namespaces()
                for svc in services.items:
                    resources.append(ResourceInfo(
                        id=f"{svc.metadata.namespace}/{svc.metadata.name}",
                        name=svc.metadata.name,
                        type="service",
                        status="active",
                        metadata={
                            "namespace": svc.metadata.namespace,
                            "type": svc.spec.type,
                            "cluster_ip": svc.spec.cluster_ip
                        }
                    ))

        except Exception as e:
            logger.error(f"Error listing K8s resources: {e}")

        return resources

    def delete_deployment(self, deployment_id: str) -> bool:
        """Delete a Kubernetes deployment."""
        if not self._get_k8s_clients():
            return False

        try:
            parts = deployment_id.split("/")
            namespace = parts[0] if len(parts) > 1 else "default"
            name = parts[-1]

            # Delete deployment
            self._apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace
            )

            # Also delete service
            try:
                self._core_v1.delete_namespaced_service(
                    name=name,
                    namespace=namespace
                )
            except Exception:
                pass

            return True

        except Exception as e:
            logger.error(f"Error deleting deployment: {e}")
            return False

    def get_config_schema(self) -> Dict[str, Any]:
        """Get Kubernetes-specific deployment configuration schema."""
        schema = super().get_config_schema()
        schema["properties"].update({
            "namespace": {"type": "string", "default": "default"},
            "app_name": {"type": "string"},
            "service_type": {
                "type": "string",
                "enum": ["ClusterIP", "NodePort", "LoadBalancer"],
                "default": "ClusterIP"
            },
            "ingress": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "default": False},
                    "host": {"type": "string"},
                    "path": {"type": "string", "default": "/"},
                    "tls": {"type": "boolean", "default": False}
                }
            }
        })
        return schema
