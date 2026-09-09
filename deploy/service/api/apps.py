"""
Apps Management Endpoints - List, status, logs, restart, remove
"""

import os
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.docker_service import DockerService
from services.nginx_service import NginxService
from services.registry_service import RegistryService

router = APIRouter()
logger = logging.getLogger(__name__)


class AppInfo(BaseModel):
    """Application information model."""
    name: str
    status: str
    container_id: Optional[str] = None
    version: int
    url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AppListResponse(BaseModel):
    """Response for listing apps."""
    apps: List[AppInfo]
    total: int


class AppStatusResponse(BaseModel):
    """Detailed app status response."""
    name: str
    status: str
    container_id: Optional[str] = None
    container_status: Optional[str] = None
    image: Optional[str] = None
    version: int
    url: str
    path: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    health: Optional[dict] = None
    resources: Optional[dict] = None


class AppLogsResponse(BaseModel):
    """Response for app logs."""
    name: str
    logs: str
    lines: int


class DeploymentLog(BaseModel):
    """Deployment log entry."""
    version: int
    status: str
    message: str
    timestamp: str


class ActionResponse(BaseModel):
    """Generic action response."""
    success: bool
    message: str


@router.get("/apps", response_model=AppListResponse)
async def list_apps(
    status: Optional[str] = Query(None, description="Filter by status (running, stopped, failed)")
):
    """
    List all deployed applications.

    Args:
        status: Optional filter by app status

    Returns:
        List of deployed applications
    """
    registry = RegistryService()
    apps = registry.list_apps(status_filter=status)

    base_url = os.environ.get('QUANTUM_BASE_URL', 'http://localhost')

    app_list = [
        AppInfo(
            name=app.name,
            status=app.status,
            container_id=app.container_id[:12] if app.container_id else None,
            version=app.version,
            url=f"{base_url}/{app.name}/",
            created_at=app.created_at.isoformat() if app.created_at else None,
            updated_at=app.updated_at.isoformat() if app.updated_at else None
        )
        for app in apps
    ]

    return AppListResponse(apps=app_list, total=len(app_list))


@router.get("/apps/{name}", response_model=AppStatusResponse)
async def get_app_status(name: str):
    """
    Get detailed status of a specific application.

    Args:
        name: Application name

    Returns:
        Detailed app status including container info and resources
    """
    registry = RegistryService()
    docker_svc = DockerService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    base_url = os.environ.get('QUANTUM_BASE_URL', 'http://localhost')

    # Get container details
    container_status = None
    health = None
    resources = None

    if app.container_id:
        try:
            container_info = docker_svc.get_container_info(f"quantum-{name}")
            container_status = container_info.get('status')
            health = container_info.get('health')
            resources = container_info.get('resources')
        except Exception as e:
            logger.warning(f"Failed to get container info: {e}")
            container_status = "unknown"

    return AppStatusResponse(
        name=app.name,
        status=app.status,
        container_id=app.container_id[:12] if app.container_id else None,
        container_status=container_status,
        image=app.image_tag,
        version=app.version,
        url=f"{base_url}/{app.name}/",
        path=app.path,
        created_at=app.created_at.isoformat() if app.created_at else None,
        updated_at=app.updated_at.isoformat() if app.updated_at else None,
        health=health,
        resources=resources
    )


@router.get("/apps/{name}/logs", response_model=AppLogsResponse)
async def get_app_logs(
    name: str,
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to retrieve"),
    since: Optional[str] = Query(None, description="Show logs since timestamp (ISO format)")
):
    """
    Get logs from an application container.

    Args:
        name: Application name
        lines: Number of log lines to retrieve (default: 100)
        since: Optional timestamp to filter logs

    Returns:
        Container logs
    """
    registry = RegistryService()
    docker_svc = DockerService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    try:
        logs = docker_svc.get_container_logs(
            f"quantum-{name}",
            tail=lines,
            since=since
        )
        return AppLogsResponse(name=name, logs=logs, lines=lines)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.get("/apps/{name}/deployments", response_model=List[DeploymentLog])
async def get_deployment_history(
    name: str,
    limit: int = Query(10, ge=1, le=100, description="Number of entries to retrieve")
):
    """
    Get deployment history for an application.

    Args:
        name: Application name
        limit: Number of history entries

    Returns:
        List of deployment log entries
    """
    registry = RegistryService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    deployments = registry.get_deployment_logs(name, limit=limit)

    return [
        DeploymentLog(
            version=d.version,
            status=d.status,
            message=d.message,
            timestamp=d.timestamp.isoformat()
        )
        for d in deployments
    ]


@router.post("/apps/{name}/restart", response_model=ActionResponse)
async def restart_app(name: str):
    """
    Restart an application container.

    Args:
        name: Application name

    Returns:
        Action result
    """
    registry = RegistryService()
    docker_svc = DockerService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    try:
        docker_svc.restart_container(f"quantum-{name}")

        # Update status
        registry.update_app_status(name, 'running')

        logger.info(f"App {name} restarted successfully")

        return ActionResponse(
            success=True,
            message=f"App '{name}' restarted successfully"
        )

    except Exception as e:
        logger.error(f"Failed to restart app {name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart app: {str(e)}"
        )


@router.post("/apps/{name}/stop", response_model=ActionResponse)
async def stop_app(name: str):
    """
    Stop an application container.

    Args:
        name: Application name

    Returns:
        Action result
    """
    registry = RegistryService()
    docker_svc = DockerService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    try:
        docker_svc.stop_container(f"quantum-{name}")

        # Update status
        registry.update_app_status(name, 'stopped')

        logger.info(f"App {name} stopped successfully")

        return ActionResponse(
            success=True,
            message=f"App '{name}' stopped successfully"
        )

    except Exception as e:
        logger.error(f"Failed to stop app {name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop app: {str(e)}"
        )


@router.post("/apps/{name}/start", response_model=ActionResponse)
async def start_app(name: str):
    """
    Start a stopped application container.

    Args:
        name: Application name

    Returns:
        Action result
    """
    registry = RegistryService()
    docker_svc = DockerService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    try:
        docker_svc.start_container(f"quantum-{name}")

        # Update status
        registry.update_app_status(name, 'running')

        logger.info(f"App {name} started successfully")

        return ActionResponse(
            success=True,
            message=f"App '{name}' started successfully"
        )

    except Exception as e:
        logger.error(f"Failed to start app {name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start app: {str(e)}"
        )


@router.delete("/apps/{name}", response_model=ActionResponse)
async def remove_app(name: str, keep_data: bool = Query(False, description="Keep app data files")):
    """
    Remove an application completely.

    Stops container, removes image, deletes nginx config, and optionally removes data.

    Args:
        name: Application name
        keep_data: If True, keep app files on disk

    Returns:
        Action result
    """
    registry = RegistryService()
    docker_svc = DockerService()
    nginx_svc = NginxService()

    app = registry.get_app(name)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    errors = []

    # Stop and remove container
    try:
        docker_svc.stop_container(f"quantum-{name}")
        docker_svc.remove_container(f"quantum-{name}")
    except Exception as e:
        errors.append(f"Container: {e}")
        logger.warning(f"Failed to remove container for {name}: {e}")

    # Remove nginx config
    try:
        nginx_svc.remove_app_config(name)
        nginx_svc.reload()
    except Exception as e:
        errors.append(f"Nginx: {e}")
        logger.warning(f"Failed to remove nginx config for {name}: {e}")

    # Remove data files
    if not keep_data and app.path:
        try:
            import shutil
            from pathlib import Path
            app_path = Path(app.path)
            if app_path.exists():
                shutil.rmtree(app_path)
        except Exception as e:
            errors.append(f"Files: {e}")
            logger.warning(f"Failed to remove files for {name}: {e}")

    # Remove from registry
    try:
        registry.delete_app(name)
    except Exception as e:
        errors.append(f"Registry: {e}")
        logger.error(f"Failed to remove app from registry: {e}")

    if errors:
        logger.warning(f"App {name} removed with errors: {errors}")
        return ActionResponse(
            success=True,
            message=f"App '{name}' removed with warnings: {'; '.join(errors)}"
        )

    logger.info(f"App {name} removed successfully")
    return ActionResponse(
        success=True,
        message=f"App '{name}' removed successfully"
    )


@router.post("/nginx/rebuild")
async def rebuild_nginx():
    """
    Rebuild nginx configuration from registered apps.

    Syncs nginx configs with the app registry, removing stale configs
    and adding missing ones, then reloads nginx.
    """
    nginx_svc = NginxService()
    registry = RegistryService()

    try:
        # Get all registered running apps
        apps = registry.list_apps()
        running_apps = {app['name'] for app in apps if app.get('status') == 'running'}

        # Remove stale nginx configs
        existing_configs = nginx_svc.list_configs()
        removed = []
        for config in existing_configs:
            if config['name'] not in running_apps:
                nginx_svc.remove_app_config(config['name'])
                removed.append(config['name'])

        # Ensure all running apps have nginx configs
        added = []
        for app in apps:
            if app.get('status') == 'running':
                name = app['name']
                nginx_svc.add_app_config(name, f"quantum-{name}", 8080)
                added.append(name)

        # Reload nginx
        reloaded = nginx_svc.reload()

        return {
            "success": reloaded,
            "message": "Nginx configuration rebuilt and reloaded" if reloaded else "Rebuild done but reload failed",
            "added": added,
            "removed": removed
        }

    except Exception as e:
        logger.error(f"Failed to rebuild nginx: {e}")
        raise HTTPException(status_code=500, detail=str(e))
