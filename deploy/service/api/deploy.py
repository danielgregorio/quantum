"""
Deploy Endpoint - Handles application uploads and deployments
"""

import os
import tarfile
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.docker_service import DockerService
from services.nginx_service import NginxService
from services.registry_service import RegistryService

router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration
APPS_DIR = os.environ.get('QUANTUM_APPS_DIR', '/data/quantum/apps')
MAX_UPLOAD_SIZE = int(os.environ.get('QUANTUM_MAX_UPLOAD_SIZE', 100 * 1024 * 1024))  # 100MB


class DeployResponse(BaseModel):
    """Response model for deploy endpoint."""
    success: bool
    message: str
    app_name: str
    url: Optional[str] = None
    container_id: Optional[str] = None
    version: Optional[int] = None


class DeployRequest(BaseModel):
    """Deploy request metadata."""
    name: str
    env_vars: Optional[dict] = None
    force: bool = False


@router.post("/deploy", response_model=DeployResponse)
async def deploy_app(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Tarball of the Quantum app"),
    name: str = Form(..., description="Application name"),
    force: bool = Form(False, description="Overwrite existing app"),
    env_vars: Optional[str] = Form(None, description="JSON encoded environment variables")
):
    """
    Deploy a new Quantum application.

    Accepts a tarball containing the app files, builds a container,
    and configures nginx routing.

    Args:
        file: Tarball (.tar.gz) of the application
        name: Application name (used for routing: /app-name/)
        force: If True, overwrite existing deployment
        env_vars: JSON string of environment variables

    Returns:
        DeployResponse with deployment status and URL
    """
    # Validate app name
    if not _validate_app_name(name):
        raise HTTPException(
            status_code=400,
            detail="Invalid app name. Use only lowercase letters, numbers, and hyphens."
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset

    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )

    # Initialize services
    registry = RegistryService()
    docker_svc = DockerService()
    nginx_svc = NginxService()

    # Check if app exists
    existing_app = registry.get_app(name)
    if existing_app and not force:
        raise HTTPException(
            status_code=409,
            detail=f"App '{name}' already exists. Use --force to overwrite."
        )

    try:
        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tarball_path = temp_path / "app.tar.gz"

            # Save uploaded file
            with open(tarball_path, 'wb') as f:
                content = await file.read()
                f.write(content)

            # Validate tarball
            if not _validate_tarball(tarball_path):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid tarball. Must contain valid Quantum app files."
                )

            # Extract tarball
            extract_dir = temp_path / "extracted"
            extract_dir.mkdir()

            with tarfile.open(tarball_path, 'r:gz') as tar:
                # Security: Check for path traversal
                for member in tar.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid tarball: contains unsafe paths"
                        )
                tar.extractall(extract_dir)

            # Copy to apps directory
            app_dir = Path(APPS_DIR) / name
            if app_dir.exists():
                shutil.rmtree(app_dir)
            shutil.copytree(extract_dir, app_dir)

            # Copy Quantum runtime files needed for Docker build
            # Default paths match Dockerfile.deploy-service layout
            app_base = Path(os.environ.get('QUANTUM_APP_BASE', '/app'))

            # Copy Dockerfile (from /app/deploy/Dockerfile)
            dockerfile_src = app_base / 'deploy' / 'Dockerfile'
            if dockerfile_src.exists():
                shutil.copy(dockerfile_src, app_dir / 'Dockerfile')
            else:
                # Fallback to legacy path
                legacy_dockerfile = Path('/home/abathur/quantum-deploy/Dockerfile')
                if legacy_dockerfile.exists():
                    shutil.copy(legacy_dockerfile, app_dir / 'Dockerfile')

            # Copy requirements.txt (from /app/quantum-requirements.txt)
            requirements_src = app_base / 'quantum-requirements.txt'
            if requirements_src.exists():
                shutil.copy(requirements_src, app_dir / 'requirements.txt')
            else:
                # Fallback to legacy path
                legacy_requirements = Path('/home/abathur/quantum-deploy/requirements.txt')
                if legacy_requirements.exists():
                    shutil.copy(legacy_requirements, app_dir / 'requirements.txt')

            # Copy src/ directory (from /app/quantum-src/)
            # First check if the tarball includes a src/ override
            tarball_src = app_dir / 'src'
            has_tarball_src = tarball_src.exists()
            tarball_src_backup = None

            # If tarball has src/, back it up to merge later
            if has_tarball_src:
                tarball_src_backup = app_dir / '_src_override'
                shutil.move(tarball_src, tarball_src_backup)

            # Copy base quantum source
            src_dir = app_base / 'quantum-src'
            if src_dir.exists():
                dest_src = app_dir / 'src'
                shutil.copytree(src_dir, dest_src)
            else:
                # Fallback to legacy path
                legacy_src = Path('/home/abathur/quantum-deploy/src')
                if legacy_src.exists():
                    dest_src = app_dir / 'src'
                    shutil.copytree(legacy_src, dest_src)

            # Merge tarball src/ overrides on top (allows updating individual files)
            if tarball_src_backup and tarball_src_backup.exists():
                dest_src = app_dir / 'src'
                for item in tarball_src_backup.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(tarball_src_backup)
                        dest_file = dest_src / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_file)
                        logger.info(f"Override applied: {rel_path}")
                shutil.rmtree(tarball_src_backup)

            # Parse environment variables
            env_dict = {}
            if env_vars:
                import json
                try:
                    env_dict = json.loads(env_vars)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid env_vars JSON format"
                    )

            # Stop existing container if exists
            if existing_app:
                try:
                    docker_svc.stop_container(f"quantum-{name}")
                    docker_svc.remove_container(f"quantum-{name}")
                except Exception as e:
                    logger.warning(f"Failed to stop existing container: {e}")

            # Build Docker image
            logger.info(f"Building Docker image for {name}...")
            image_tag = f"quantum-{name}:latest"
            docker_svc.build_image(
                path=str(app_dir),
                tag=image_tag
            )

            # Run container
            logger.info(f"Starting container for {name}...")
            container_id = docker_svc.run_container(
                image=image_tag,
                name=f"quantum-{name}",
                network="quantum-net",
                env_vars=env_dict,
                labels={
                    "quantum.app": name,
                    "quantum.managed": "true"
                }
            )

            # Update nginx config
            logger.info(f"Configuring nginx for {name}...")
            nginx_svc.add_app_config(name, f"quantum-{name}", 8080)
            nginx_svc.reload()

            # Get version
            version = (existing_app.version + 1) if existing_app else 1

            # Register in database
            registry.upsert_app(
                name=name,
                container_id=container_id,
                image_tag=image_tag,
                status='running',
                path=str(app_dir),
                env_vars=env_dict,
                version=version
            )

            # Log deployment
            registry.log_deployment(
                app_name=name,
                version=version,
                status='success',
                message=f"Deployed successfully to container {container_id[:12]}"
            )

            # Determine URL
            base_url = os.environ.get('QUANTUM_BASE_URL', 'http://localhost')
            app_url = f"{base_url}/{name}/"

            logger.info(f"App {name} deployed successfully at {app_url}")

            return DeployResponse(
                success=True,
                message=f"App '{name}' deployed successfully",
                app_name=name,
                url=app_url,
                container_id=container_id[:12],
                version=version
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deploy failed for {name}: {e}")

        # Log failed deployment
        registry.log_deployment(
            app_name=name,
            version=0,
            status='failed',
            message=str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=f"Deployment failed: {str(e)}"
        )


def _validate_app_name(name: str) -> bool:
    """Validate application name."""
    import re
    # Only lowercase letters, numbers, and hyphens
    # Must start with letter, 3-50 chars
    pattern = r'^[a-z][a-z0-9-]{2,49}$'
    return bool(re.match(pattern, name))


def _validate_tarball(path: Path) -> bool:
    """Validate that tarball contains a Quantum app."""
    try:
        with tarfile.open(path, 'r:gz') as tar:
            names = tar.getnames()

            # Must have at least one .q file or quantum.config.yaml
            has_quantum_files = any(
                n.endswith('.q') or n.endswith('quantum.config.yaml')
                for n in names
            )

            if not has_quantum_files:
                return False

            # Check total extracted size (prevent zip bombs)
            total_size = sum(m.size for m in tar.getmembers())
            if total_size > 500 * 1024 * 1024:  # 500MB extracted
                return False

            return True

    except Exception:
        return False
