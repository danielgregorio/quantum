"""
Docker Service for Quantum Admin
Manages Docker containers for database datasources
"""
import docker
from docker.errors import DockerException, NotFound, APIError
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class DockerService:
    """Service for managing Docker containers"""

    # Default database images
    DEFAULT_IMAGES = {
        "postgres": "postgres:16-alpine",
        "mysql": "mysql:8.0",
        "mongodb": "mongo:7.0",
        "redis": "redis:7.2-alpine",
        "mariadb": "mariadb:11.2"
    }

    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
            logger.info("✅ Docker client connected successfully")
        except DockerException as e:
            logger.error(f"❌ Failed to connect to Docker: {e}")
            raise RuntimeError(
                "Docker is not running or not accessible. "
                "Please ensure Docker Desktop is running."
            )

    def get_default_image(self, db_type: str) -> str:
        """Get default Docker image for a database type"""
        return self.DEFAULT_IMAGES.get(db_type.lower(), "")

    def pull_image(self, image_name: str) -> bool:
        """
        Pull Docker image from registry

        Args:
            image_name: Full image name (e.g., "postgres:16-alpine")

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"📥 Pulling image: {image_name}")
            self.client.images.pull(image_name)
            logger.info(f"✅ Successfully pulled image: {image_name}")
            return True
        except APIError as e:
            logger.error(f"❌ Failed to pull image {image_name}: {e}")
            return False

    def create_container(
        self,
        name: str,
        image: str,
        port: int,
        env_vars: Dict[str, str],
        auto_start: bool = False
    ) -> Optional[str]:
        """
        Create and optionally start a database container

        Args:
            name: Container name (must be unique)
            image: Docker image to use
            port: Host port to map to container
            env_vars: Environment variables (credentials, config)
            auto_start: Whether to start the container immediately

        Returns:
            str: Container ID if successful, None otherwise
        """
        try:
            # Ensure image exists
            try:
                self.client.images.get(image)
            except NotFound:
                logger.info(f"Image {image} not found locally, pulling...")
                if not self.pull_image(image):
                    return None

            # Determine internal port based on database type
            internal_port = self._get_internal_port(image)

            # Create container
            logger.info(f"🐳 Creating container: {name}")
            container = self.client.containers.create(
                image=image,
                name=name,
                ports={f"{internal_port}/tcp": port},
                environment=env_vars,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )

            logger.info(f"✅ Container created: {name} (ID: {container.short_id})")

            # Start if auto_start is enabled
            if auto_start:
                self.start_container(container.id)

            return container.id

        except APIError as e:
            logger.error(f"❌ Failed to create container {name}: {e}")
            return None

    def start_container(self, container_id: str) -> bool:
        """
        Start a container

        Args:
            container_id: Container ID or name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(container_id)

            # Check if already running
            container.reload()
            if container.status == "running":
                logger.info(f"ℹ️ Container {container_id} is already running")
                return True

            logger.info(f"▶️ Starting container: {container_id}")
            container.start()
            logger.info(f"✅ Container started: {container_id}")
            return True

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return False
        except APIError as e:
            logger.error(f"❌ Failed to start container {container_id}: {e}")
            return False

    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        Stop a container gracefully

        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before killing

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(container_id)

            # Check if already stopped
            container.reload()
            if container.status != "running":
                logger.info(f"ℹ️ Container {container_id} is not running")
                return True

            logger.info(f"⏹️ Stopping container: {container_id}")
            container.stop(timeout=timeout)
            logger.info(f"✅ Container stopped: {container_id}")
            return True

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return False
        except APIError as e:
            logger.error(f"❌ Failed to stop container {container_id}: {e}")
            return False

    def restart_container(self, container_id: str, timeout: int = 10) -> bool:
        """
        Restart a container

        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before killing

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(container_id)
            logger.info(f"🔄 Restarting container: {container_id}")
            container.restart(timeout=timeout)
            logger.info(f"✅ Container restarted: {container_id}")
            return True

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return False
        except APIError as e:
            logger.error(f"❌ Failed to restart container {container_id}: {e}")
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """
        Remove a container

        Args:
            container_id: Container ID or name
            force: Force removal even if running

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            container = self.client.containers.get(container_id)

            # Stop first if running and not forcing
            if not force:
                container.reload()
                if container.status == "running":
                    self.stop_container(container_id)

            logger.info(f"🗑️ Removing container: {container_id}")
            container.remove(force=force)
            logger.info(f"✅ Container removed: {container_id}")
            return True

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return False
        except APIError as e:
            logger.error(f"❌ Failed to remove container {container_id}: {e}")
            return False

    def get_container_status(self, container_id: str) -> Optional[Dict]:
        """
        Get container status and health information

        Args:
            container_id: Container ID or name

        Returns:
            dict: Status information or None if not found
        """
        try:
            container = self.client.containers.get(container_id)
            container.reload()

            # Get detailed stats
            status_info = {
                "id": container.id,
                "short_id": container.short_id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "created": container.attrs.get("Created", ""),
                "ports": container.ports,
                "environment": container.attrs.get("Config", {}).get("Env", [])
            }

            # Add health check if available
            health = container.attrs.get("State", {}).get("Health", {})
            if health:
                status_info["health"] = health.get("Status", "unknown")
                status_info["health_log"] = health.get("Log", [])[-1] if health.get("Log") else None

            return status_info

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return None
        except APIError as e:
            logger.error(f"❌ Failed to get container status {container_id}: {e}")
            return None

    def get_container_logs(
        self,
        container_id: str,
        lines: int = 100,
        timestamps: bool = True
    ) -> Optional[str]:
        """
        Get container logs

        Args:
            container_id: Container ID or name
            lines: Number of lines to retrieve (tail)
            timestamps: Include timestamps in output

        Returns:
            str: Log output or None if not found
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(
                tail=lines,
                timestamps=timestamps
            ).decode("utf-8")

            return logs

        except NotFound:
            logger.error(f"❌ Container not found: {container_id}")
            return None
        except APIError as e:
            logger.error(f"❌ Failed to get logs for {container_id}: {e}")
            return None

    def list_containers(self, all: bool = False) -> List[Dict]:
        """
        List all containers

        Args:
            all: Include stopped containers

        Returns:
            list: List of container information
        """
        try:
            containers = self.client.containers.list(all=all)

            return [
                {
                    "id": c.id,
                    "short_id": c.short_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "ports": c.ports
                }
                for c in containers
            ]

        except APIError as e:
            logger.error(f"❌ Failed to list containers: {e}")
            return []

    def _get_internal_port(self, image: str) -> int:
        """Get default internal port for database image"""
        if "postgres" in image.lower():
            return 5432
        elif "mysql" in image.lower() or "mariadb" in image.lower():
            return 3306
        elif "mongo" in image.lower():
            return 27017
        elif "redis" in image.lower():
            return 6379
        else:
            return 5432  # Default fallback

    def get_used_ports(self) -> List[int]:
        """
        Get all ports currently in use by Docker containers

        Returns:
            list: List of host ports in use
        """
        used_ports = []
        try:
            containers = self.client.containers.list(all=True)
            for container in containers:
                if container.ports:
                    for container_port, host_bindings in container.ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                if 'HostPort' in binding:
                                    used_ports.append(int(binding['HostPort']))
            return used_ports
        except APIError as e:
            logger.error(f"Failed to get used ports: {e}")
            return []

    def find_available_port(self, preferred_port: int, max_attempts: int = 100) -> int:
        """
        Find an available port starting from preferred_port

        Args:
            preferred_port: The port to start searching from
            max_attempts: Maximum number of ports to try

        Returns:
            int: Available port number
        """
        used_ports = self.get_used_ports()
        port = preferred_port

        for _ in range(max_attempts):
            if port not in used_ports:
                return port
            port += 1

        raise RuntimeError(f"Could not find available port after {max_attempts} attempts starting from {preferred_port}")
