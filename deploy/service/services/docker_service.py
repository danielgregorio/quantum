"""
Docker Service - Container and image management
"""

import os
import logging
from typing import Optional, Dict, List, Any
import docker
from docker.errors import NotFound, APIError, BuildError

logger = logging.getLogger(__name__)


class DockerService:
    """Service for managing Docker containers and images."""

    def __init__(self):
        """Initialize Docker client."""
        self.client = docker.from_env()
        self.network_name = os.environ.get('QUANTUM_DOCKER_NETWORK', 'quantum-net')
        self._ensure_network()

    def _ensure_network(self):
        """Ensure the quantum network exists."""
        try:
            self.client.networks.get(self.network_name)
        except NotFound:
            logger.info(f"Creating Docker network: {self.network_name}")
            self.client.networks.create(
                self.network_name,
                driver="bridge",
                labels={"quantum.managed": "true"}
            )

    def build_image(
        self,
        path: str,
        tag: str,
        dockerfile_path: Optional[str] = None
    ) -> str:
        """
        Build a Docker image from a directory.

        Args:
            path: Path to the build context
            tag: Image tag (e.g., "quantum-myapp:latest")
            dockerfile_path: Path to Dockerfile (default: path/Dockerfile)

        Returns:
            Image ID
        """
        # Use global Dockerfile if app doesn't have its own
        dockerfile = "Dockerfile"
        if dockerfile_path and os.path.exists(dockerfile_path):
            dockerfile = dockerfile_path

        logger.info(f"Building image {tag} from {path}")

        try:
            image, logs = self.client.images.build(
                path=path,
                tag=tag,
                dockerfile=dockerfile,
                rm=True,  # Remove intermediate containers
                nocache=True,  # Force rebuild to pick up code changes
                labels={
                    "quantum.managed": "true",
                    "quantum.app": tag.split(':')[0].replace('quantum-', '')
                }
            )

            # Log build output
            for chunk in logs:
                if 'stream' in chunk:
                    logger.debug(chunk['stream'].strip())

            logger.info(f"Image {tag} built successfully: {image.id[:12]}")
            return image.id

        except BuildError as e:
            logger.error(f"Build failed: {e}")
            raise
        except APIError as e:
            logger.error(f"Docker API error: {e}")
            raise

    def run_container(
        self,
        image: str,
        name: str,
        network: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Run a new container.

        Args:
            image: Image tag to run
            name: Container name
            network: Docker network (default: quantum-net)
            env_vars: Environment variables
            labels: Container labels
            ports: Port mappings (not used for internal network)

        Returns:
            Container ID
        """
        network = network or self.network_name

        # Default labels
        all_labels = {
            "quantum.managed": "true",
        }
        if labels:
            all_labels.update(labels)

        logger.info(f"Starting container {name} from image {image}")

        try:
            container = self.client.containers.run(
                image=image,
                name=name,
                network=network,
                environment=env_vars or {},
                labels=all_labels,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                # No port mapping - accessed via internal network
            )

            logger.info(f"Container {name} started: {container.id[:12]}")
            return container.id

        except APIError as e:
            logger.error(f"Failed to start container: {e}")
            raise

    def stop_container(self, name: str, timeout: int = 10):
        """Stop a running container."""
        try:
            container = self.client.containers.get(name)
            container.stop(timeout=timeout)
            logger.info(f"Container {name} stopped")
        except NotFound:
            logger.warning(f"Container {name} not found")
        except APIError as e:
            logger.error(f"Failed to stop container {name}: {e}")
            raise

    def start_container(self, name: str):
        """Start a stopped container."""
        try:
            container = self.client.containers.get(name)
            container.start()
            logger.info(f"Container {name} started")
        except NotFound:
            logger.error(f"Container {name} not found")
            raise
        except APIError as e:
            logger.error(f"Failed to start container {name}: {e}")
            raise

    def restart_container(self, name: str, timeout: int = 10):
        """Restart a container."""
        try:
            container = self.client.containers.get(name)
            container.restart(timeout=timeout)
            logger.info(f"Container {name} restarted")
        except NotFound:
            logger.error(f"Container {name} not found")
            raise
        except APIError as e:
            logger.error(f"Failed to restart container {name}: {e}")
            raise

    def remove_container(self, name: str, force: bool = True):
        """Remove a container."""
        try:
            container = self.client.containers.get(name)
            container.remove(force=force)
            logger.info(f"Container {name} removed")
        except NotFound:
            logger.warning(f"Container {name} not found")
        except APIError as e:
            logger.error(f"Failed to remove container {name}: {e}")
            raise

    def get_container_info(self, name: str) -> Dict[str, Any]:
        """Get detailed container information."""
        try:
            container = self.client.containers.get(name)

            # Get stats (non-blocking)
            stats = container.stats(stream=False)

            # Calculate resource usage
            resources = None
            if stats:
                try:
                    # CPU usage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                   stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0

                    # Memory usage
                    mem_usage = stats['memory_stats'].get('usage', 0)
                    mem_limit = stats['memory_stats'].get('limit', 1)
                    mem_percent = (mem_usage / mem_limit) * 100.0

                    resources = {
                        'cpu_percent': round(cpu_percent, 2),
                        'memory_usage_mb': round(mem_usage / (1024 * 1024), 2),
                        'memory_limit_mb': round(mem_limit / (1024 * 1024), 2),
                        'memory_percent': round(mem_percent, 2)
                    }
                except (KeyError, ZeroDivisionError):
                    pass

            # Health status
            health = None
            if 'Health' in container.attrs.get('State', {}):
                health_state = container.attrs['State']['Health']
                health = {
                    'status': health_state.get('Status'),
                    'failing_streak': health_state.get('FailingStreak', 0)
                }

            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else None,
                'created': container.attrs.get('Created'),
                'started': container.attrs.get('State', {}).get('StartedAt'),
                'health': health,
                'resources': resources
            }

        except NotFound:
            raise ValueError(f"Container {name} not found")
        except APIError as e:
            logger.error(f"Failed to get container info: {e}")
            raise

    def get_container_logs(
        self,
        name: str,
        tail: int = 100,
        since: Optional[str] = None
    ) -> str:
        """Get container logs."""
        try:
            container = self.client.containers.get(name)

            kwargs = {
                'tail': tail,
                'timestamps': True,
                'stdout': True,
                'stderr': True
            }

            if since:
                from datetime import datetime
                # Parse ISO timestamp
                kwargs['since'] = datetime.fromisoformat(since.replace('Z', '+00:00'))

            logs = container.logs(**kwargs)
            return logs.decode('utf-8', errors='replace')

        except NotFound:
            raise ValueError(f"Container {name} not found")
        except APIError as e:
            logger.error(f"Failed to get logs: {e}")
            raise

    def list_quantum_containers(self) -> List[Dict[str, Any]]:
        """List all Quantum-managed containers."""
        containers = self.client.containers.list(
            all=True,
            filters={"label": "quantum.managed=true"}
        )

        return [
            {
                'id': c.id[:12],
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else 'unknown',
                'labels': c.labels
            }
            for c in containers
        ]

    def remove_image(self, tag: str, force: bool = False):
        """Remove a Docker image."""
        try:
            self.client.images.remove(tag, force=force)
            logger.info(f"Image {tag} removed")
        except NotFound:
            logger.warning(f"Image {tag} not found")
        except APIError as e:
            logger.error(f"Failed to remove image {tag}: {e}")
            raise
