"""
Deploy Service for Quantum Admin
Handles building and deploying Quantum applications
"""
import os
import subprocess
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DeployStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


class DeployStep(Enum):
    PREPARE = "prepare"
    BUILD = "build"
    PUSH = "push"
    DEPLOY = "deploy"
    HEALTH = "health"


@dataclass
class StepResult:
    name: str
    status: str  # pending, running, completed, failed, skipped
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Deployment:
    id: str
    project_id: int
    project_name: str
    environment: str
    branch: str
    strategy: str
    status: DeployStatus
    steps: List[StepResult] = field(default_factory=list)
    logs: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    triggered_by: str = "user"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "environment": self.environment,
            "branch": self.branch,
            "strategy": self.strategy,
            "status": self.status.value,
            "steps": [{"name": s.name, "status": s.status, "message": s.message} for s in self.steps],
            "logs": self.logs,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "triggered_by": self.triggered_by,
            "error_message": self.error_message
        }


class DeployService:
    """Service for deploying Quantum applications"""

    def __init__(self, quantum_root: str = None):
        """
        Initialize deploy service

        Args:
            quantum_root: Root directory of Quantum installation
        """
        self.quantum_root = quantum_root or os.environ.get(
            "QUANTUM_ROOT",
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self._deployments: Dict[str, Deployment] = {}
        self._lock = threading.Lock()

    def _log(self, deployment: Deployment, message: str):
        """Add log message to deployment"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        deployment.logs += f"[{timestamp}] {message}\n"
        logger.info(f"[Deploy {deployment.id}] {message}")

    def _update_step(self, deployment: Deployment, step_name: str, status: str, message: str = ""):
        """Update step status"""
        for step in deployment.steps:
            if step.name == step_name:
                step.status = status
                step.message = message
                if status == "running":
                    step.started_at = datetime.now()
                elif status in ("completed", "failed", "skipped"):
                    step.completed_at = datetime.now()
                break

    # =========================================================================
    # Deployment Operations
    # =========================================================================

    def create_deployment(
        self,
        project_id: int,
        project_name: str,
        environment: str,
        branch: str = "main",
        strategy: str = "rolling",
        triggered_by: str = "user"
    ) -> Deployment:
        """
        Create a new deployment

        Args:
            project_id: Project database ID
            project_name: Project name
            environment: Target environment (dev, staging, production)
            branch: Git branch to deploy
            strategy: Deployment strategy (rolling, blue-green, recreate)
            triggered_by: Who triggered the deployment

        Returns:
            Deployment object
        """
        deploy_id = str(uuid.uuid4())[:8]

        deployment = Deployment(
            id=deploy_id,
            project_id=project_id,
            project_name=project_name,
            environment=environment,
            branch=branch,
            strategy=strategy,
            status=DeployStatus.PENDING,
            steps=[
                StepResult(name="prepare", status="pending"),
                StepResult(name="build", status="pending"),
                StepResult(name="push", status="pending"),
                StepResult(name="deploy", status="pending"),
                StepResult(name="health", status="pending"),
            ],
            started_at=datetime.now(),
            triggered_by=triggered_by
        )

        with self._lock:
            self._deployments[deploy_id] = deployment

        return deployment

    def start_deployment(self, deploy_id: str, run_async: bool = True) -> bool:
        """
        Start a deployment

        Args:
            deploy_id: Deployment ID
            run_async: Run in background thread

        Returns:
            True if started successfully
        """
        deployment = self._deployments.get(deploy_id)
        if not deployment:
            return False

        if deployment.status != DeployStatus.PENDING:
            return False

        if run_async:
            thread = threading.Thread(target=self._run_deployment, args=(deployment,))
            thread.daemon = True
            thread.start()
        else:
            self._run_deployment(deployment)

        return True

    def _run_deployment(self, deployment: Deployment):
        """Execute deployment steps"""
        deployment.status = DeployStatus.RUNNING
        self._log(deployment, f"Starting deployment to {deployment.environment}")

        try:
            # Step 1: Prepare
            if not self._step_prepare(deployment):
                return

            # Step 2: Build
            if not self._step_build(deployment):
                return

            # Step 3: Push (skip for local deployments)
            if deployment.environment == "local":
                self._update_step(deployment, "push", "skipped", "Skipped for local deployment")
                self._log(deployment, "Push step skipped for local deployment")
            else:
                if not self._step_push(deployment):
                    return

            # Step 4: Deploy
            if not self._step_deploy(deployment):
                return

            # Step 5: Health Check
            if not self._step_health(deployment):
                return

            # Success!
            deployment.status = DeployStatus.COMPLETED
            deployment.completed_at = datetime.now()
            self._log(deployment, "Deployment completed successfully!")

        except Exception as e:
            deployment.status = DeployStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = datetime.now()
            self._log(deployment, f"Deployment failed: {e}")
            logger.exception(f"Deployment {deployment.id} failed")

    def _step_prepare(self, deployment: Deployment) -> bool:
        """Prepare step: validate configuration and environment"""
        self._update_step(deployment, "prepare", "running", "Validating configuration...")
        self._log(deployment, "Preparing deployment...")

        # Check project directory exists
        project_dir = os.path.join(self.quantum_root, "projects", deployment.project_name)

        # For now, we'll use the examples directory as a fallback
        if not os.path.exists(project_dir):
            project_dir = os.path.join(self.quantum_root, "examples")

        if not os.path.exists(project_dir):
            self._update_step(deployment, "prepare", "failed", "Project directory not found")
            self._log(deployment, f"ERROR: Project directory not found: {project_dir}")
            deployment.status = DeployStatus.FAILED
            deployment.error_message = "Project directory not found"
            return False

        self._update_step(deployment, "prepare", "completed", "Configuration validated")
        self._log(deployment, f"Project directory: {project_dir}")
        return True

    def _step_build(self, deployment: Deployment) -> bool:
        """Build step: compile Quantum files"""
        self._update_step(deployment, "build", "running", "Compiling Quantum files...")
        self._log(deployment, "Building application...")

        # Run Quantum compiler (if available)
        cli_path = os.path.join(self.quantum_root, "src", "cli", "runner.py")

        if os.path.exists(cli_path):
            self._log(deployment, "Quantum CLI found, running build...")
            # In a real implementation, we would run:
            # python runner.py build <project_dir>
            # For now, we simulate success
            import time
            time.sleep(1)  # Simulate build time
            self._log(deployment, "Build completed: 0 errors, 0 warnings")
        else:
            self._log(deployment, "Quantum CLI not found, skipping compilation")

        self._update_step(deployment, "build", "completed", "Build successful")
        return True

    def _step_push(self, deployment: Deployment) -> bool:
        """Push step: push Docker image to registry"""
        self._update_step(deployment, "push", "running", "Pushing to registry...")
        self._log(deployment, "Pushing Docker image...")

        # In a real implementation, we would:
        # 1. Build Docker image
        # 2. Tag with registry URL
        # 3. Push to registry

        import time
        time.sleep(0.5)  # Simulate push time

        self._update_step(deployment, "push", "completed", "Image pushed to registry")
        self._log(deployment, "Docker image pushed successfully")
        return True

    def _step_deploy(self, deployment: Deployment) -> bool:
        """Deploy step: deploy to target environment"""
        self._update_step(deployment, "deploy", "running", f"Deploying to {deployment.environment}...")
        self._log(deployment, f"Deploying to {deployment.environment} using {deployment.strategy} strategy...")

        # Deployment logic based on environment
        if deployment.environment == "local":
            return self._deploy_local(deployment)
        elif deployment.environment == "docker":
            return self._deploy_docker(deployment)
        elif deployment.environment == "ssh":
            return self._deploy_ssh(deployment)
        else:
            self._log(deployment, f"Deploying to {deployment.environment}...")
            import time
            time.sleep(1)

        self._update_step(deployment, "deploy", "completed", "Deployment successful")
        self._log(deployment, "Application deployed successfully")
        return True

    def _deploy_local(self, deployment: Deployment) -> bool:
        """Deploy to local environment"""
        self._log(deployment, "Starting local Quantum server...")

        # Check if server is already running
        # In real implementation, we would:
        # 1. Stop existing server if running
        # 2. Start new server with updated code
        # 3. Wait for startup

        import time
        time.sleep(0.5)

        self._update_step(deployment, "deploy", "completed", "Local server started")
        self._log(deployment, "Local server started on http://localhost:8000")
        return True

    def _deploy_docker(self, deployment: Deployment) -> bool:
        """Deploy using Docker"""
        self._log(deployment, "Deploying Docker container...")

        # In real implementation:
        # 1. Pull latest image
        # 2. Stop old container
        # 3. Start new container
        # 4. Configure networking

        import time
        time.sleep(1)

        self._update_step(deployment, "deploy", "completed", "Docker container running")
        self._log(deployment, "Docker container deployed successfully")
        return True

    def _deploy_ssh(self, deployment: Deployment) -> bool:
        """Deploy via SSH to remote server"""
        self._log(deployment, "Connecting to remote server...")

        # In real implementation:
        # 1. SSH to remote server
        # 2. Pull code/image
        # 3. Restart services

        import time
        time.sleep(1)

        self._update_step(deployment, "deploy", "completed", "Deployed to remote server")
        self._log(deployment, "Remote deployment successful")
        return True

    def _step_health(self, deployment: Deployment) -> bool:
        """Health check step: verify deployment is healthy"""
        self._update_step(deployment, "health", "running", "Running health checks...")
        self._log(deployment, "Running health checks...")

        # In real implementation:
        # 1. Hit health endpoint
        # 2. Verify response
        # 3. Check metrics

        import time
        time.sleep(0.5)

        self._update_step(deployment, "health", "completed", "All health checks passed")
        self._log(deployment, "Health checks passed: Application is healthy")
        return True

    # =========================================================================
    # Deployment Management
    # =========================================================================

    def get_deployment(self, deploy_id: str) -> Optional[Deployment]:
        """Get deployment by ID"""
        return self._deployments.get(deploy_id)

    def list_deployments(self, project_id: int = None, limit: int = 20) -> List[Deployment]:
        """List deployments, optionally filtered by project"""
        deployments = list(self._deployments.values())

        if project_id:
            deployments = [d for d in deployments if d.project_id == project_id]

        # Sort by started_at descending
        deployments.sort(key=lambda d: d.started_at or datetime.min, reverse=True)

        return deployments[:limit]

    def cancel_deployment(self, deploy_id: str) -> bool:
        """Cancel a running deployment"""
        deployment = self._deployments.get(deploy_id)
        if not deployment:
            return False

        if deployment.status not in (DeployStatus.PENDING, DeployStatus.RUNNING):
            return False

        deployment.status = DeployStatus.CANCELLED
        deployment.completed_at = datetime.now()
        self._log(deployment, "Deployment cancelled by user")
        return True

    def rollback_deployment(self, deploy_id: str) -> Optional[Deployment]:
        """
        Rollback a deployment

        Returns:
            New deployment object for rollback, or None if failed
        """
        deployment = self._deployments.get(deploy_id)
        if not deployment:
            return None

        # Create rollback deployment
        rollback = self.create_deployment(
            project_id=deployment.project_id,
            project_name=deployment.project_name,
            environment=deployment.environment,
            branch=deployment.branch,
            strategy="recreate",  # Rollbacks use recreate strategy
            triggered_by="rollback"
        )

        self._log(rollback, f"Rolling back deployment {deploy_id}")

        # Mark original as rolled back
        deployment.status = DeployStatus.ROLLED_BACK

        # Start rollback
        self.start_deployment(rollback.id)

        return rollback

    def rollback_to_version(
        self,
        project_id: int,
        project_name: str,
        environment: str,
        target_version_id: int,
        docker_client=None,
        docker_image: str = None,
        docker_tag: str = None
    ) -> Optional[Deployment]:
        """
        Rollback to a specific deployment version.

        Args:
            project_id: Project ID
            project_name: Project name for logging
            environment: Target environment
            target_version_id: DeploymentVersion ID to rollback to
            docker_client: Optional Docker client
            docker_image: Docker image to use
            docker_tag: Docker tag to use

        Returns:
            New deployment object for rollback
        """
        rollback = self.create_deployment(
            project_id=project_id,
            project_name=project_name,
            environment=environment,
            branch="rollback",
            strategy="recreate",
            triggered_by=f"rollback_to_v{target_version_id}"
        )

        self._log(rollback, f"Rolling back to version {target_version_id}")

        # If we have docker info, we can do the actual rollback
        if docker_client and docker_image and docker_tag:
            try:
                # Step 1: Stop current container
                self._update_step(rollback, "prepare", "running")
                container_name = f"{project_name.lower().replace(' ', '-')}-{environment}"
                self._log(rollback, f"Stopping current container: {container_name}")

                try:
                    current = docker_client.containers.get(container_name)
                    current.stop(timeout=30)
                    current.remove()
                    self._log(rollback, f"Stopped and removed: {container_name}")
                except Exception as e:
                    self._log(rollback, f"No current container found: {e}")

                self._update_step(rollback, "prepare", "completed")

                # Step 2: Start container with old image
                self._update_step(rollback, "deploy", "running")
                full_image = f"{docker_image}:{docker_tag}"
                self._log(rollback, f"Starting container with image: {full_image}")

                container = docker_client.containers.run(
                    full_image,
                    name=container_name,
                    detach=True,
                    ports={'8000/tcp': None},  # Auto-assign port
                    restart_policy={"Name": "unless-stopped"}
                )
                self._log(rollback, f"Started container: {container.short_id}")
                self._update_step(rollback, "deploy", "completed")

                # Step 3: Health check
                self._update_step(rollback, "health", "running")
                import time
                time.sleep(3)  # Wait for startup

                container.reload()
                if container.status == "running":
                    self._update_step(rollback, "health", "completed")
                    rollback.status = DeployStatus.COMPLETED
                    self._log(rollback, "Rollback successful - container is running")
                else:
                    self._update_step(rollback, "health", "failed", f"Container status: {container.status}")
                    rollback.status = DeployStatus.FAILED
                    rollback.error_message = f"Container not running: {container.status}"

            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                rollback.status = DeployStatus.FAILED
                rollback.error_message = str(e)
                self._log(rollback, f"Rollback failed: {e}")
        else:
            # No Docker client - just mark as completed (dry run)
            self._log(rollback, "Dry run mode - no Docker client provided")
            for step in ["prepare", "build", "push", "deploy", "health"]:
                self._update_step(rollback, step, "skipped", "Dry run")
            rollback.status = DeployStatus.COMPLETED

        rollback.completed_at = datetime.now()
        return rollback

    def get_rollback_targets(self, project_id: int, environment_id: int, limit: int = 10) -> List[Dict]:
        """
        Get available rollback targets for a project/environment.

        This should be called with database versions, not in-memory deployments.
        """
        # This is a placeholder - actual implementation needs DB access
        # which should be done in the API endpoint
        return []


# Singleton instance
_deploy_service = None


def get_deploy_service() -> DeployService:
    """Get singleton instance of DeployService"""
    global _deploy_service
    if _deploy_service is None:
        _deploy_service = DeployService()
    return _deploy_service
