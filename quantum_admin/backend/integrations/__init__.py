"""
Cloud Integrations Package for Quantum Admin
Provides connectors for AWS, Kubernetes, Azure, and GCP
"""

from .base import CloudConnector, CloudProvider, DeploymentResult
from .aws_connector import AWSConnector
from .k8s_connector import KubernetesConnector
from .azure_connector import AzureConnector
from .gcp_connector import GCPConnector

__all__ = [
    'CloudConnector',
    'CloudProvider',
    'DeploymentResult',
    'AWSConnector',
    'KubernetesConnector',
    'AzureConnector',
    'GCPConnector',
]


def get_connector(provider: str, credentials: dict) -> CloudConnector:
    """Factory function to get the appropriate connector."""
    connectors = {
        'aws': AWSConnector,
        'kubernetes': KubernetesConnector,
        'k8s': KubernetesConnector,
        'azure': AzureConnector,
        'gcp': GCPConnector,
    }

    connector_class = connectors.get(provider.lower())
    if not connector_class:
        raise ValueError(f"Unknown cloud provider: {provider}")

    return connector_class(credentials)
