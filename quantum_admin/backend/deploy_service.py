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
                return

        # A name that matches no step wrote nowhere and said nothing — a
        # typo here made a whole step's status silently vanish from the
        # screen, which then showed it as still pending.
        logger.warning(
            "deployment %s has no step named %r; the %r update was dropped",
            deployment.id, step_name, status)

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

    def _mark_failed(self, deployment: Deployment, step_name: str):
        """Registra a falha do deploy no proprio objeto.

        Um passo que devolvia False fazia `return` daqui e mais nada: o
        status continuava RUNNING para sempre. E a rota que a interface le
        (`main.py`) responde

            "completed": status in ("completed", "failed", "cancelled", ...)
            "failed":    status == "failed"

        entao um build que falhou aparecia como `completed=false,
        failed=false` — um spinner que nunca para, sem erro nenhum na tela,
        para um deploy que ja tinha terminado e dado errado. So o
        `_step_prepare` marcava FAILED por conta propria; os outros quatro
        passos, nao.
        """
        deployment.status = DeployStatus.FAILED
        deployment.completed_at = datetime.now()
        if not deployment.error_message:
            passo = next(
                (s for s in deployment.steps if s.name == step_name), None)
            deployment.error_message = (
                getattr(passo, 'message', None)
                or f"the '{step_name}' step failed"
            )
        self._log(deployment,
                  f"Deployment failed at the '{step_name}' step: "
                  f"{deployment.error_message}")

    def _run_deployment(self, deployment: Deployment):
        """Execute deployment steps"""
        deployment.status = DeployStatus.RUNNING
        self._log(deployment, f"Starting deployment to {deployment.environment}")

        try:
            # Step 1: Prepare
            if not self._step_prepare(deployment):
                return self._mark_failed(deployment, "prepare")

            # Step 2: Build
            if not self._step_build(deployment):
                return self._mark_failed(deployment, "build")

            # Step 3: Push (skip for local deployments)
            if deployment.environment == "local":
                self._update_step(deployment, "push", "skipped", "Skipped for local deployment")
                self._log(deployment, "Push step skipped for local deployment")
            else:
                if not self._step_push(deployment):
                    return self._mark_failed(deployment, "push")

            # Step 4: Deploy
            if not self._step_deploy(deployment):
                return self._mark_failed(deployment, "deploy")

            # Step 5: Health Check
            if not self._step_health(deployment):
                return self._mark_failed(deployment, "health")

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

        # The Quantum CLI moved from src/cli/runner.py to the installed
        # package (FRAMEWORK_PLAN Fase 1.1), so this always took the
        # "not found" branch.
        cli_path = os.path.join(self.quantum_root, "quantum", "cli", "runner.py")

        if not os.path.exists(cli_path):
            # It used to log "Quantum CLI not found, skipping compilation" and
            # then mark the step "completed / Build successful" anyway. A
            # deployment that never compiled anything reported a green build.
            self._log(deployment, f"Quantum CLI not found at {cli_path}")
            self._update_step(
                deployment, "build", "failed",
                "Quantum CLI not found — nothing was compiled"
            )
            return False

        # Really parse the project's .q files with the real parser, instead of
        # the time.sleep(1) + "Build completed: 0 errors, 0 warnings" this used
        # to print without invoking anything.
        #
        # Parsing is what "build" means for a .q project — there is no compile
        # step to a binary — so this is the whole check, not a stand-in for
        # one. A file that does not parse is a 400 in production, which is
        # exactly what a deploy gate should stop.
        project_dir = os.path.join(self.quantum_root, "projects", deployment.project_name)
        if not os.path.exists(project_dir):
            project_dir = os.path.join(self.quantum_root, "examples")

        try:
            from quantum.core.parser import QuantumParser
        except ImportError as e:
            self._log(deployment, f"ERROR: cannot import the Quantum parser: {e}")
            self._update_step(deployment, "build", "failed",
                              "Quantum parser not importable")
            return False

        parser = QuantumParser()
        ok, failures = 0, []
        for root, _dirs, files in os.walk(project_dir):
            for fname in files:
                if not fname.endswith('.q'):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, encoding='utf-8', errors='ignore') as fh:
                        parser.parse(fh.read())
                    ok += 1
                except Exception as e:
                    failures.append((os.path.relpath(path, project_dir), str(e).split('\n')[0]))

        for rel, err in failures:
            self._log(deployment, f"  FAIL {rel}: {err[:160]}")

        if failures:
            self._log(deployment,
                      f"Build failed: {ok} file(s) parsed, {len(failures)} failed")
            self._update_step(
                deployment, "build", "failed",
                f"{len(failures)} file(s) do not parse"
            )
            deployment.status = DeployStatus.FAILED
            deployment.error_message = f"{len(failures)} .q file(s) failed to parse"
            return False

        if ok == 0:
            self._log(deployment, f"No .q files found under {project_dir}")
            self._update_step(deployment, "build", "failed",
                              "No .q files to build")
            return False

        self._log(deployment, f"Build completed: {ok} file(s) parsed, 0 errors")
        self._update_step(deployment, "build", "completed",
                          f"{ok} file(s) parsed")
        return True

    # A note that covers this step and the deploy ones below.
    #
    # These slept for half a second and then reported "Image pushed to
    # registry", "Deployment successful", "Local server started on
    # http://localhost:8000" and "Health checks passed: Application is
    # healthy". Nothing was pushed, deployed or checked. The comment inside
    # each one said "in a real implementation, we would…" — invisible from
    # the screen, which showed a green pipeline.
    #
    # Telling someone their application is deployed and healthy when nothing
    # ran is the most expensive lie this codebase told. So: the health check
    # is implemented for real below, and every step that cannot do its work
    # now FAILS and says why. A deploy button that reports failure is
    # useless; one that reports success is dangerous.
    _NOT_IMPLEMENTED = (
        "not implemented: this step does no work. It used to report success "
        "anyway. See PRODUCTION_READINESS.md."
    )

    def _step_push(self, deployment: Deployment) -> bool:
        """Push step: push a Docker image to the registry. Not implemented."""
        self._update_step(deployment, "push", "running", "Pushing to registry...")

        self._update_step(deployment, "push", "failed", self._NOT_IMPLEMENTED)
        self._log(deployment,
                  "push: no image is built or pushed — step not implemented")
        return False

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
            self._update_step(
                deployment, "deploy", "failed",
                f"unknown environment {deployment.environment!r}")
            self._log(deployment,
                      f"deploy: no handler for environment "
                      f"{deployment.environment!r}")
            return False

    def _deploy_local(self, deployment: Deployment) -> bool:
        """Deploy to the local environment. Not implemented."""
        self._update_step(deployment, "deploy", "failed", self._NOT_IMPLEMENTED)
        self._log(deployment,
                  "deploy(local): no server is started — step not implemented. "
                  "Run the app yourself with `quantum start`.")
        return False

    def _deploy_docker(self, deployment: Deployment) -> bool:
        """Deploy with Docker. Not implemented.

        DockerService can pull, create, start and stop containers, but there
        is no image build anywhere in the admin, so there is nothing to run.
        """
        self._update_step(deployment, "deploy", "failed", self._NOT_IMPLEMENTED)
        self._log(deployment,
                  "deploy(docker): no image is built and no container is "
                  "started — step not implemented")
        return False

    def _deploy_ssh(self, deployment: Deployment) -> bool:
        """Deploy over SSH. Not implemented."""
        self._update_step(deployment, "deploy", "failed", self._NOT_IMPLEMENTED)
        self._log(deployment,
                  "deploy(ssh): nothing is copied and nothing is restarted — "
                  "step not implemented")
        return False

    def _step_health(self, deployment: Deployment, timeout: float = 10.0) -> bool:
        """Health check step: actually request the health endpoint.

        This one CAN be done honestly — it is an HTTP GET — so it is. It was
        a sleep followed by "Health checks passed: Application is healthy".
        """
        self._update_step(deployment, "health", "running", "Running health checks...")

        url = self._health_url(deployment)
        if not url:
            self._update_step(
                deployment, "health", "skipped",
                "no health URL configured for this environment")
            self._log(deployment,
                      "health: no URL configured — nothing was checked")
            return True

        self._log(deployment, f"health: GET {url}")
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=timeout) as response:
                code = response.getcode()
        except Exception as exc:
            self._update_step(deployment, "health", "failed",
                              f"{url} did not answer: {exc}")
            self._log(deployment, f"health: FAILED — {exc}")
            return False

        if 200 <= code < 400:
            self._update_step(deployment, "health", "completed",
                              f"{url} answered {code}")
            self._log(deployment, f"health: {url} answered {code}")
            return True

        self._update_step(deployment, "health", "failed",
                          f"{url} answered {code}")
        self._log(deployment, f"health: FAILED — {url} answered {code}")
        return False

    def _health_url(self, deployment: Deployment) -> Optional[str]:
        """The health URL for this deployment's environment, if configured."""
        try:
            from .settings_service import get_settings_service
        except ImportError:
            from settings_service import get_settings_service

        try:
            settings = get_settings_service().get_global_settings()
        except Exception:
            return None

        deployment_cfg = settings.get("deployment") or {}
        for env in deployment_cfg.get("environments") or []:
            if isinstance(env, dict) and env.get("name") == deployment.environment:
                if env.get("health_url"):
                    return env["health_url"]
                host = env.get("host")
                if host:
                    path = deployment_cfg.get("health_check_path", "/health")
                    port = deployment_cfg.get("default_port", 8080)
                    return f"http://{host}:{port}{path}"
        return None

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
