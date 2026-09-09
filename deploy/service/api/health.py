"""
Health Check Endpoints
"""

import os
import docker
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns service status for load balancers and monitoring.
    """
    # Check Docker connectivity
    docker_status = "healthy"
    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        docker_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if docker_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {
            "docker": docker_status,
            "apps_dir": os.path.exists(os.environ.get('QUANTUM_APPS_DIR', '/data/quantum/apps')),
            "nginx_dir": os.path.exists(os.environ.get('QUANTUM_NGINX_DIR', '/data/quantum/nginx')),
        }
    }


@router.get("/health/detailed")
async def health_detailed():
    """
    Detailed health check with system information.
    """
    import psutil

    # Docker info
    docker_info = {}
    try:
        client = docker.from_env()
        info = client.info()
        docker_info = {
            "status": "healthy",
            "containers_running": info.get('ContainersRunning', 0),
            "containers_total": info.get('Containers', 0),
            "images": info.get('Images', 0),
        }
    except Exception as e:
        docker_info = {"status": "unhealthy", "error": str(e)}

    # System resources
    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
    }

    return {
        "status": "healthy" if docker_info.get("status") == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "docker": docker_info,
        "system": system_info,
    }
