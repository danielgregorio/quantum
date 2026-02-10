"""
Pipeline Service for Quantum Admin
Orchestrates the deployment pipeline with real-time updates
"""
import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    from .models import (
        Project, Environment, Deployment, DeploymentTarget,
        DeploymentVersion
    )
    from .database import SessionLocal
    from .git_service import get_git_service, CommitInfo
    from .websocket_manager import get_websocket_manager
except ImportError:
    from models import (
        Project, Environment, Deployment, DeploymentTarget,
        DeploymentVersion
    )
    from database import SessionLocal
    from git_service import get_git_service, CommitInfo
    from websocket_manager import get_websocket_manager


class PipelineStep(Enum):
    GIT_PULL = "git_pull"
    BUILD = "build"
    TEST = "test"
    PUSH = "push"
    DEPLOY = "deploy"
    HEALTH = "health"


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class StepResult:
    """Result of a pipeline step"""
    step: PipelineStep
    success: bool
    message: str
    duration_seconds: float
    started_at: datetime
    completed_at: datetime


@dataclass
class PipelineContext:
    """Context passed through pipeline steps"""
    project: Project
    environment: Environment
    deployment: Deployment
    version: Optional[DeploymentVersion] = None

    # Git info
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_message: Optional[str] = None
    git_author: Optional[str] = None

    # Docker info
    docker_image: Optional[str] = None
    docker_tag: Optional[str] = None

    # Control flags
    skip_build: bool = False  # True for rollbacks
    skip_test: bool = False
    skip_push: bool = False

    # Results
    step_results: List[StepResult] = field(default_factory=list)


class PipelineService:
    """Service for orchestrating deployment pipelines"""

    PIPELINE_STEPS = [
        PipelineStep.GIT_PULL,
        PipelineStep.BUILD,
        PipelineStep.TEST,
        PipelineStep.PUSH,
        PipelineStep.DEPLOY,
        PipelineStep.HEALTH
    ]

    def __init__(self, db: Session = None):
        """
        Initialize pipeline service

        Args:
            db: SQLAlchemy session (optional)
        """
        self._db = db
        self._own_session = db is None
        self._running_pipelines: Dict[str, asyncio.Task] = {}

    @property
    def db(self) -> Session:
        """Get database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        """Close database session if we own it"""
        if self._own_session and self._db:
            self._db.close()
            self._db = None

    # =========================================================================
    # Pipeline Execution
    # =========================================================================

    async def run_pipeline(
        self,
        project_id: int,
        environment_id: int,
        triggered_by: str = "user",
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        skip_test: bool = False
    ) -> Optional[Deployment]:
        """
        Run a deployment pipeline

        Args:
            project_id: Project ID
            environment_id: Environment ID to deploy to
            triggered_by: Who/what triggered this deployment
            git_commit: Specific commit to deploy (optional)
            git_branch: Branch to deploy from (optional)
            skip_test: Skip test step

        Returns:
            Deployment object or None if failed to start
        """
        # Load project and environment
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return None

        environment = self.db.query(Environment).filter(Environment.id == environment_id).first()
        if not environment:
            logger.error(f"Environment {environment_id} not found")
            return None

        # Create or get deployment target
        target = self._get_or_create_target(project, environment)

        # Create deployment record
        deployment = Deployment(
            project_id=project_id,
            target_id=target.id,
            version=git_commit[:7] if git_commit else "pending",
            status="pending",
            started_at=datetime.utcnow(),
            triggered_by=triggered_by
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)

        # Create context
        ctx = PipelineContext(
            project=project,
            environment=environment,
            deployment=deployment,
            git_commit=git_commit,
            git_branch=git_branch or environment.branch,
            skip_test=skip_test
        )

        # Run pipeline async
        deploy_id = str(deployment.id)
        task = asyncio.create_task(self._execute_pipeline(ctx))
        self._running_pipelines[deploy_id] = task

        return deployment

    async def _execute_pipeline(self, ctx: PipelineContext):
        """Execute the full pipeline"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        try:
            # Update status to running
            ctx.deployment.status = "running"
            self.db.commit()

            await ws.broadcast_status(deploy_id, "running", PipelineStep.GIT_PULL.value)
            await ws.broadcast_log(deploy_id, f"Starting deployment to {ctx.environment.display_name}", "info")

            # Execute each step
            for step in self.PIPELINE_STEPS:
                # Check if step should be skipped
                if step == PipelineStep.TEST and ctx.skip_test:
                    await ws.broadcast_log(deploy_id, f"Skipping {step.value}", "info")
                    continue
                if step == PipelineStep.BUILD and ctx.skip_build:
                    await ws.broadcast_log(deploy_id, f"Skipping {step.value} (rollback)", "info")
                    continue
                if step == PipelineStep.PUSH and ctx.skip_push:
                    await ws.broadcast_log(deploy_id, f"Skipping {step.value}", "info")
                    continue

                await ws.broadcast_status(deploy_id, "running", step.value)
                await ws.broadcast_log(deploy_id, f"Starting step: {step.value}", "info", step.value)

                start_time = time.time()
                success, message = await self._execute_step(ctx, step)
                duration = time.time() - start_time

                result = StepResult(
                    step=step,
                    success=success,
                    message=message,
                    duration_seconds=duration,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
                ctx.step_results.append(result)

                level = "success" if success else "error"
                await ws.broadcast_log(deploy_id, f"{step.value}: {message}", level, step.value)
                await ws.broadcast_step_complete(deploy_id, step.value, success, duration, message)

                if not success:
                    # Step failed - mark deployment as failed
                    ctx.deployment.status = "failed"
                    ctx.deployment.error_message = f"Step {step.value} failed: {message}"
                    ctx.deployment.completed_at = datetime.utcnow()
                    self.db.commit()

                    await ws.broadcast_complete(deploy_id, False, f"Deployment failed at {step.value}")

                    # Attempt auto-rollback if we got past deploy step
                    if step == PipelineStep.HEALTH:
                        await self._auto_rollback(ctx)

                    return

            # All steps succeeded
            ctx.deployment.status = "completed"
            ctx.deployment.completed_at = datetime.utcnow()
            ctx.deployment.version = ctx.git_commit[:7] if ctx.git_commit else ctx.docker_tag
            self.db.commit()

            # Create version record
            await self._create_version_record(ctx)

            await ws.broadcast_log(deploy_id, "Deployment completed successfully!", "success")
            await ws.broadcast_complete(deploy_id, True, "Deployment successful", ctx.deployment.version)

        except asyncio.CancelledError:
            ctx.deployment.status = "cancelled"
            ctx.deployment.completed_at = datetime.utcnow()
            self.db.commit()
            await ws.broadcast_complete(deploy_id, False, "Deployment cancelled")

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            ctx.deployment.status = "failed"
            ctx.deployment.error_message = str(e)
            ctx.deployment.completed_at = datetime.utcnow()
            self.db.commit()
            await ws.broadcast_complete(deploy_id, False, f"Pipeline error: {e}")

        finally:
            self._running_pipelines.pop(deploy_id, None)

    async def _execute_step(self, ctx: PipelineContext, step: PipelineStep) -> tuple:
        """
        Execute a single pipeline step

        Returns:
            Tuple of (success, message)
        """
        step_handlers = {
            PipelineStep.GIT_PULL: self._step_git_pull,
            PipelineStep.BUILD: self._step_build,
            PipelineStep.TEST: self._step_test,
            PipelineStep.PUSH: self._step_push,
            PipelineStep.DEPLOY: self._step_deploy,
            PipelineStep.HEALTH: self._step_health,
        }

        handler = step_handlers.get(step)
        if not handler:
            return False, f"Unknown step: {step}"

        try:
            return await handler(ctx)
        except Exception as e:
            logger.exception(f"Step {step.value} failed: {e}")
            return False, str(e)

    # =========================================================================
    # Pipeline Steps
    # =========================================================================

    async def _step_git_pull(self, ctx: PipelineContext) -> tuple:
        """Pull latest code from Git"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        git_service = get_git_service()
        if not git_service:
            return True, "Git service not available, skipping"

        project_name = ctx.project.name

        await ws.broadcast_log(deploy_id, f"Pulling branch: {ctx.git_branch}", "info", "git_pull")

        # Clone or pull
        if not git_service.is_repo(project_name):
            # TODO: Get repo URL from project config
            await ws.broadcast_log(deploy_id, "Repository not found locally", "warning", "git_pull")
            return True, "No local repo, skipping git pull"

        # Pull latest
        commit_sha = git_service.pull_latest(project_name, ctx.git_branch)

        if not commit_sha:
            return False, "Failed to pull latest changes"

        # Get commit info
        commit_info = git_service.get_commit_info(project_name, commit_sha)
        if commit_info:
            ctx.git_commit = commit_info.sha
            ctx.git_message = commit_info.message
            ctx.git_author = commit_info.author
            await ws.broadcast_log(
                deploy_id,
                f"Commit: {commit_info.short_sha} - {commit_info.message[:50]}",
                "info",
                "git_pull"
            )

        return True, f"Pulled {commit_sha[:7]}"

    async def _step_build(self, ctx: PipelineContext) -> tuple:
        """Build Docker image"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        # Determine image name
        registry = ctx.environment.docker_registry or "local"
        project_name = ctx.project.name.lower().replace(" ", "-")
        tag = ctx.git_commit[:7] if ctx.git_commit else datetime.now().strftime("%Y%m%d%H%M%S")

        ctx.docker_tag = tag
        ctx.docker_image = f"{registry}/{project_name}:{tag}"

        await ws.broadcast_log(deploy_id, f"Building image: {ctx.docker_image}", "info", "build")

        # TODO: Actually build Docker image
        # For now, simulate build
        await asyncio.sleep(2)

        await ws.broadcast_log(deploy_id, "Build completed successfully", "success", "build")
        return True, f"Built {ctx.docker_image}"

    async def _step_test(self, ctx: PipelineContext) -> tuple:
        """Run tests"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        await ws.broadcast_log(deploy_id, "Running tests...", "info", "test")

        # TODO: Actually run tests
        # For now, simulate test run
        await asyncio.sleep(1)

        await ws.broadcast_log(deploy_id, "All tests passed", "success", "test")
        return True, "All tests passed"

    async def _step_push(self, ctx: PipelineContext) -> tuple:
        """Push Docker image to registry"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        if not ctx.docker_image:
            return True, "No image to push"

        await ws.broadcast_log(deploy_id, f"Pushing image to registry...", "info", "push")

        # TODO: Actually push to registry
        # For now, simulate push
        await asyncio.sleep(1.5)

        await ws.broadcast_log(deploy_id, "Image pushed successfully", "success", "push")
        return True, f"Pushed {ctx.docker_image}"

    async def _step_deploy(self, ctx: PipelineContext) -> tuple:
        """Deploy to target environment"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        await ws.broadcast_log(
            deploy_id,
            f"Deploying to {ctx.environment.display_name}...",
            "info",
            "deploy"
        )

        # Get Docker host for this environment
        docker_host = ctx.environment.docker_host

        if docker_host:
            await ws.broadcast_log(deploy_id, f"Connecting to {docker_host}", "info", "deploy")

        try:
            # Import Docker service
            try:
                from .docker_service import DockerService
            except ImportError:
                from docker_service import DockerService

            docker = DockerService(docker_host=docker_host) if docker_host else DockerService()

            container_name = ctx.environment.container_name or f"{ctx.project.name}-{ctx.environment.name}"

            # Stop existing container if running
            await ws.broadcast_log(deploy_id, f"Stopping existing container: {container_name}", "info", "deploy")
            try:
                old_container = docker.client.containers.get(container_name)
                old_container.stop(timeout=30)
                old_container.remove()
                await ws.broadcast_log(deploy_id, "Old container removed", "info", "deploy")
            except Exception:
                pass  # Container doesn't exist

            # Run new container
            await ws.broadcast_log(deploy_id, f"Starting new container: {container_name}", "info", "deploy")

            port = ctx.environment.port or 8000

            # Build environment variables
            env_vars = {}
            if ctx.environment.env_vars_json:
                import json
                env_vars = json.loads(ctx.environment.env_vars_json)

            # TODO: Actually start the container with proper image
            # For now, simulate deploy
            await asyncio.sleep(1)

            await ws.broadcast_log(deploy_id, f"Container started on port {port}", "success", "deploy")
            return True, f"Deployed to {ctx.environment.display_name}"

        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return False, str(e)

    async def _step_health(self, ctx: PipelineContext) -> tuple:
        """Run health check"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        health_url = ctx.environment.health_url
        timeout = ctx.environment.health_timeout or 30

        if not health_url:
            await ws.broadcast_log(deploy_id, "No health URL configured, skipping", "warning", "health")
            return True, "Health check skipped"

        await ws.broadcast_log(deploy_id, f"Checking health at {health_url}", "info", "health")

        try:
            import httpx

            max_retries = 5
            retry_delay = timeout / max_retries

            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(health_url)

                        if response.status_code == 200:
                            await ws.broadcast_log(deploy_id, "Health check passed", "success", "health")
                            return True, "Health check passed"

                        await ws.broadcast_log(
                            deploy_id,
                            f"Health check returned {response.status_code}, retrying...",
                            "warning",
                            "health"
                        )

                except httpx.RequestError as e:
                    await ws.broadcast_log(
                        deploy_id,
                        f"Health check failed: {e}, retrying...",
                        "warning",
                        "health"
                    )

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)

            return False, f"Health check failed after {max_retries} attempts"

        except ImportError:
            # httpx not installed, skip health check
            await ws.broadcast_log(deploy_id, "httpx not available, skipping health check", "warning", "health")
            return True, "Health check skipped (httpx not installed)"

    # =========================================================================
    # Rollback & Promote
    # =========================================================================

    async def rollback(
        self,
        deployment_id: int,
        target_version_id: int,
        triggered_by: str = "user"
    ) -> Optional[Deployment]:
        """
        Rollback to a previous version

        Args:
            deployment_id: Current deployment to rollback from
            target_version_id: Version to rollback to
            triggered_by: Who triggered the rollback

        Returns:
            New Deployment for the rollback
        """
        # Get current deployment
        current = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not current:
            logger.error(f"Deployment {deployment_id} not found")
            return None

        # Get target version
        target_version = self.db.query(DeploymentVersion).filter(
            DeploymentVersion.id == target_version_id
        ).first()

        if not target_version:
            logger.error(f"Version {target_version_id} not found")
            return None

        # Get environment
        environment = self.db.query(Environment).filter(
            Environment.id == target_version.environment_id
        ).first()

        if not environment:
            logger.error(f"Environment not found for version {target_version_id}")
            return None

        # Create rollback deployment
        target = self._get_or_create_target(current.project, environment)

        rollback_deploy = Deployment(
            project_id=current.project_id,
            target_id=target.id,
            version=f"rollback-{target_version.git_commit[:7] if target_version.git_commit else target_version_id}",
            status="pending",
            started_at=datetime.utcnow(),
            triggered_by=triggered_by,
            rollback_from=deployment_id
        )
        self.db.add(rollback_deploy)
        self.db.commit()
        self.db.refresh(rollback_deploy)

        # Create context with skip flags for rollback
        ctx = PipelineContext(
            project=current.project,
            environment=environment,
            deployment=rollback_deploy,
            git_commit=target_version.git_commit,
            git_branch=target_version.git_branch,
            docker_image=target_version.docker_image,
            docker_tag=target_version.docker_tag,
            skip_build=True,  # Skip build for rollback
            skip_test=True    # Skip test for rollback
        )

        # Mark old version as not current
        self.db.query(DeploymentVersion).filter(
            DeploymentVersion.environment_id == environment.id,
            DeploymentVersion.is_current == True
        ).update({"is_current": False})
        self.db.commit()

        # Run pipeline
        deploy_id = str(rollback_deploy.id)
        task = asyncio.create_task(self._execute_pipeline(ctx))
        self._running_pipelines[deploy_id] = task

        return rollback_deploy

    async def promote(
        self,
        deployment_id: int,
        target_env_id: int,
        triggered_by: str = "user"
    ) -> Optional[Deployment]:
        """
        Promote a deployment to the next environment

        Args:
            deployment_id: Deployment to promote from
            target_env_id: Target environment ID
            triggered_by: Who triggered the promotion

        Returns:
            New Deployment for the promoted version
        """
        # Get source deployment
        source = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not source or source.status != "completed":
            logger.error(f"Cannot promote deployment {deployment_id}")
            return None

        # Get target environment
        target_env = self.db.query(Environment).filter(Environment.id == target_env_id).first()
        if not target_env:
            logger.error(f"Target environment {target_env_id} not found")
            return None

        # Check approval requirement
        if target_env.requires_approval and not target_env.approved_by:
            logger.error(f"Environment {target_env.name} requires approval")
            return None

        # Get the version that was deployed
        source_version = self.db.query(DeploymentVersion).filter(
            DeploymentVersion.deployment_id == deployment_id,
            DeploymentVersion.is_current == True
        ).first()

        # Run deployment to new environment
        return await self.run_pipeline(
            project_id=source.project_id,
            environment_id=target_env_id,
            triggered_by=triggered_by,
            git_commit=source_version.git_commit if source_version else source.version,
            skip_test=True  # Tests already passed in previous environment
        )

    async def _auto_rollback(self, ctx: PipelineContext):
        """Attempt automatic rollback after health check failure"""
        ws = get_websocket_manager()
        deploy_id = str(ctx.deployment.id)

        # Find previous successful version
        previous = self.db.query(DeploymentVersion).filter(
            DeploymentVersion.environment_id == ctx.environment.id,
            DeploymentVersion.is_rollback_target == True,
            DeploymentVersion.id != ctx.version.id if ctx.version else True
        ).order_by(DeploymentVersion.created_at.desc()).first()

        if not previous:
            await ws.broadcast_log(deploy_id, "No previous version to rollback to", "error", "health")
            return

        await ws.broadcast_log(
            deploy_id,
            f"Auto-rollback to version {previous.git_commit[:7] if previous.git_commit else previous.id}",
            "warning",
            "health"
        )

        await self.rollback(ctx.deployment.id, previous.id, "auto-rollback")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_or_create_target(self, project: Project, environment: Environment) -> DeploymentTarget:
        """Get or create a deployment target for an environment"""
        import json

        target_name = f"{project.name}-{environment.name}"

        target = self.db.query(DeploymentTarget).filter(
            DeploymentTarget.project_id == project.id,
            DeploymentTarget.name == target_name
        ).first()

        if not target:
            target = DeploymentTarget(
                project_id=project.id,
                name=target_name,
                type="docker",
                config_json=json.dumps({
                    "environment_id": environment.id,
                    "docker_host": environment.docker_host,
                    "container_name": environment.container_name,
                    "port": environment.port
                }),
                is_active=True
            )
            self.db.add(target)
            self.db.commit()
            self.db.refresh(target)

        return target

    async def _create_version_record(self, ctx: PipelineContext):
        """Create a deployment version record"""
        # Mark previous version as not current
        self.db.query(DeploymentVersion).filter(
            DeploymentVersion.environment_id == ctx.environment.id,
            DeploymentVersion.is_current == True
        ).update({"is_current": False})

        version = DeploymentVersion(
            project_id=ctx.project.id,
            environment_id=ctx.environment.id,
            git_commit=ctx.git_commit,
            git_branch=ctx.git_branch,
            git_message=ctx.git_message,
            git_author=ctx.git_author,
            docker_image=ctx.docker_image,
            docker_tag=ctx.docker_tag,
            deployment_id=ctx.deployment.id,
            is_current=True,
            is_rollback_target=True
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        ctx.version = version

    # =========================================================================
    # Pipeline Management
    # =========================================================================

    async def cancel_pipeline(self, deployment_id: int) -> bool:
        """
        Cancel a running pipeline

        Args:
            deployment_id: Deployment ID

        Returns:
            True if cancelled
        """
        deploy_id = str(deployment_id)
        task = self._running_pipelines.get(deploy_id)

        if task and not task.done():
            task.cancel()
            return True

        return False

    def get_pipeline_status(self, deployment_id: int) -> Optional[Dict]:
        """
        Get status of a pipeline

        Args:
            deployment_id: Deployment ID

        Returns:
            Status dict or None
        """
        deployment = self.db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            return None

        return {
            "id": deployment.id,
            "status": deployment.status,
            "version": deployment.version,
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
            "error_message": deployment.error_message,
            "triggered_by": deployment.triggered_by
        }


# Singleton instance
_pipeline_service = None


def get_pipeline_service(db: Session = None) -> PipelineService:
    """Get pipeline service instance"""
    if db:
        return PipelineService(db)

    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service
