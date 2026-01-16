"""
Unit Tests for Docker Service
Tests container management, image operations, and Docker integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from docker_service import DockerService


class TestDockerServiceInit:
    """Test Docker service initialization"""

    @patch('docker_service.docker.from_env')
    def test_init_success(self, mock_docker):
        """Test successful Docker client initialization"""
        mock_client = Mock()
        mock_docker.return_value = mock_client

        service = DockerService()

        assert service.client == mock_client
        mock_docker.assert_called_once()

    @patch('docker_service.docker.from_env')
    def test_init_connection_error(self, mock_docker):
        """Test Docker initialization with connection error"""
        mock_docker.side_effect = Exception("Cannot connect to Docker daemon")

        with pytest.raises(Exception):
            DockerService()


class TestListContainers:
    """Test listing containers"""

    @patch('docker_service.docker.from_env')
    def test_list_all_containers(self, mock_docker):
        """Test listing all containers"""
        mock_container1 = Mock()
        mock_container1.id = "abc123"
        mock_container1.name = "test-container-1"
        mock_container1.status = "running"
        mock_container1.image.tags = ["nginx:latest"]

        mock_container2 = Mock()
        mock_container2.id = "def456"
        mock_container2.name = "test-container-2"
        mock_container2.status = "stopped"
        mock_container2.image.tags = ["postgres:15"]

        mock_client = Mock()
        mock_client.containers.list.return_value = [mock_container1, mock_container2]
        mock_docker.return_value = mock_client

        service = DockerService()
        containers = service.list_containers(all=True)

        assert len(containers) == 2
        assert containers[0]["name"] == "test-container-1"
        assert containers[1]["status"] == "stopped"

    @patch('docker_service.docker.from_env')
    def test_list_running_only(self, mock_docker):
        """Test listing only running containers"""
        mock_container = Mock()
        mock_container.id = "abc123"
        mock_container.name = "running-container"
        mock_container.status = "running"
        mock_container.image.tags = ["nginx:latest"]

        mock_client = Mock()
        mock_client.containers.list.return_value = [mock_container]
        mock_docker.return_value = mock_client

        service = DockerService()
        containers = service.list_containers(all=False)

        mock_client.containers.list.assert_called_with(all=False)
        assert len(containers) == 1

    @patch('docker_service.docker.from_env')
    def test_list_containers_empty(self, mock_docker):
        """Test listing when no containers exist"""
        mock_client = Mock()
        mock_client.containers.list.return_value = []
        mock_docker.return_value = mock_client

        service = DockerService()
        containers = service.list_containers()

        assert containers == []


class TestCreateContainer:
    """Test container creation"""

    @patch('docker_service.docker.from_env')
    def test_create_basic_container(self, mock_docker):
        """Test creating a basic container"""
        mock_container = Mock()
        mock_container.id = "new123"
        mock_container.name = "new-nginx"

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        result = service.create_container(
            name="new-nginx",
            image="nginx:latest"
        )

        assert result["id"] == "new123"
        assert result["name"] == "new-nginx"
        mock_client.containers.run.assert_called_once()

    @patch('docker_service.docker.from_env')
    def test_create_with_ports(self, mock_docker):
        """Test creating container with port mapping"""
        mock_container = Mock()
        mock_container.id = "web123"

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.create_container(
            name="web-server",
            image="nginx:latest",
            ports={"80/tcp": 8080}
        )

        call_args = mock_client.containers.run.call_args
        assert call_args[1]["ports"] == {"80/tcp": 8080}

    @patch('docker_service.docker.from_env')
    def test_create_with_environment(self, mock_docker):
        """Test creating container with environment variables"""
        mock_container = Mock()
        mock_container.id = "db123"

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.create_container(
            name="postgres-db",
            image="postgres:15",
            environment={"POSTGRES_PASSWORD": "secret"}
        )

        call_args = mock_client.containers.run.call_args
        assert "POSTGRES_PASSWORD" in call_args[1]["environment"]

    @patch('docker_service.docker.from_env')
    def test_create_with_volumes(self, mock_docker):
        """Test creating container with volumes"""
        mock_container = Mock()
        mock_container.id = "vol123"

        mock_client = Mock()
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.create_container(
            name="data-container",
            image="alpine",
            volumes={"/host/path": {"bind": "/container/path", "mode": "rw"}}
        )

        call_args = mock_client.containers.run.call_args
        assert "/host/path" in call_args[1]["volumes"]

    @patch('docker_service.docker.from_env')
    def test_create_container_image_not_found(self, mock_docker):
        """Test creating container with non-existent image"""
        from docker.errors import ImageNotFound

        mock_client = Mock()
        mock_client.containers.run.side_effect = ImageNotFound("Image not found")
        mock_docker.return_value = mock_client

        service = DockerService()

        with pytest.raises(ImageNotFound):
            service.create_container(name="test", image="nonexistent:latest")


class TestContainerOperations:
    """Test container start/stop/remove operations"""

    @patch('docker_service.docker.from_env')
    def test_start_container(self, mock_docker):
        """Test starting a container"""
        mock_container = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.start_container("abc123")

        mock_container.start.assert_called_once()

    @patch('docker_service.docker.from_env')
    def test_stop_container(self, mock_docker):
        """Test stopping a container"""
        mock_container = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.stop_container("abc123")

        mock_container.stop.assert_called_once()

    @patch('docker_service.docker.from_env')
    def test_restart_container(self, mock_docker):
        """Test restarting a container"""
        mock_container = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.restart_container("abc123")

        mock_container.restart.assert_called_once()

    @patch('docker_service.docker.from_env')
    def test_remove_container(self, mock_docker):
        """Test removing a container"""
        mock_container = Mock()

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.remove_container("abc123", force=True)

        mock_container.remove.assert_called_once_with(force=True)

    @patch('docker_service.docker.from_env')
    def test_container_not_found(self, mock_docker):
        """Test operations on non-existent container"""
        from docker.errors import NotFound

        mock_client = Mock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        mock_docker.return_value = mock_client

        service = DockerService()

        with pytest.raises(NotFound):
            service.start_container("nonexistent")


class TestContainerLogs:
    """Test container log retrieval"""

    @patch('docker_service.docker.from_env')
    def test_get_logs(self, mock_docker):
        """Test retrieving container logs"""
        mock_container = Mock()
        mock_container.logs.return_value = b"Log line 1\nLog line 2\n"

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        logs = service.get_container_logs("abc123")

        assert "Log line 1" in logs
        assert "Log line 2" in logs

    @patch('docker_service.docker.from_env')
    def test_get_logs_with_tail(self, mock_docker):
        """Test retrieving last N log lines"""
        mock_container = Mock()
        mock_container.logs.return_value = b"Last line\n"

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        service.get_container_logs("abc123", tail=100)

        mock_container.logs.assert_called_with(tail=100)


class TestContainerStats:
    """Test container statistics"""

    @patch('docker_service.docker.from_env')
    def test_get_stats(self, mock_docker):
        """Test retrieving container stats"""
        mock_stats = {
            "cpu_stats": {"cpu_usage": {"total_usage": 1000000}},
            "memory_stats": {"usage": 52428800}
        }

        mock_container = Mock()
        mock_container.stats.return_value = iter([mock_stats])

        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client

        service = DockerService()
        stats = service.get_container_stats("abc123")

        assert stats is not None
        assert "memory_stats" in stats


class TestImageOperations:
    """Test Docker image operations"""

    @patch('docker_service.docker.from_env')
    def test_list_images(self, mock_docker):
        """Test listing Docker images"""
        mock_image = Mock()
        mock_image.id = "img123"
        mock_image.tags = ["nginx:latest"]

        mock_client = Mock()
        mock_client.images.list.return_value = [mock_image]
        mock_docker.return_value = mock_client

        service = DockerService()
        images = service.list_images()

        assert len(images) == 1
        assert images[0]["id"] == "img123"

    @patch('docker_service.docker.from_env')
    def test_pull_image(self, mock_docker):
        """Test pulling a Docker image"""
        mock_image = Mock()

        mock_client = Mock()
        mock_client.images.pull.return_value = mock_image
        mock_docker.return_value = mock_client

        service = DockerService()
        service.pull_image("nginx:latest")

        mock_client.images.pull.assert_called_with("nginx:latest")

    @patch('docker_service.docker.from_env')
    def test_remove_image(self, mock_docker):
        """Test removing a Docker image"""
        mock_client = Mock()
        mock_docker.return_value = mock_client

        service = DockerService()
        service.remove_image("nginx:latest", force=True)

        mock_client.images.remove.assert_called_with("nginx:latest", force=True)


class TestDockerCompose:
    """Test Docker Compose operations"""

    @patch('docker_service.docker.from_env')
    def test_generate_compose_file(self, mock_docker):
        """Test generating docker-compose.yml"""
        mock_client = Mock()
        mock_docker.return_value = mock_client

        service = DockerService()

        containers_config = [
            {
                "name": "web",
                "image": "nginx:latest",
                "ports": {"80": "8080"}
            },
            {
                "name": "db",
                "image": "postgres:15",
                "environment": {"POSTGRES_PASSWORD": "secret"}
            }
        ]

        compose_yaml = service.generate_compose_file(containers_config)

        assert "version:" in compose_yaml
        assert "services:" in compose_yaml
        assert "web:" in compose_yaml
        assert "db:" in compose_yaml
        assert "nginx:latest" in compose_yaml
        assert "postgres:15" in compose_yaml


class TestNetworkOperations:
    """Test Docker network operations"""

    @patch('docker_service.docker.from_env')
    def test_list_networks(self, mock_docker):
        """Test listing Docker networks"""
        mock_network = Mock()
        mock_network.id = "net123"
        mock_network.name = "my-network"

        mock_client = Mock()
        mock_client.networks.list.return_value = [mock_network]
        mock_docker.return_value = mock_client

        service = DockerService()
        networks = service.list_networks()

        assert len(networks) == 1
        assert networks[0]["name"] == "my-network"

    @patch('docker_service.docker.from_env')
    def test_create_network(self, mock_docker):
        """Test creating a Docker network"""
        mock_network = Mock()
        mock_network.id = "net456"

        mock_client = Mock()
        mock_client.networks.create.return_value = mock_network
        mock_docker.return_value = mock_client

        service = DockerService()
        service.create_network("my-network")

        mock_client.networks.create.assert_called_with("my-network", driver="bridge")


class TestVolumeOperations:
    """Test Docker volume operations"""

    @patch('docker_service.docker.from_env')
    def test_list_volumes(self, mock_docker):
        """Test listing Docker volumes"""
        mock_volume = Mock()
        mock_volume.id = "vol123"
        mock_volume.name = "data-volume"

        mock_client = Mock()
        mock_client.volumes.list.return_value = [mock_volume]
        mock_docker.return_value = mock_client

        service = DockerService()
        volumes = service.list_volumes()

        assert len(volumes) == 1

    @patch('docker_service.docker.from_env')
    def test_create_volume(self, mock_docker):
        """Test creating a Docker volume"""
        mock_volume = Mock()

        mock_client = Mock()
        mock_client.volumes.create.return_value = mock_volume
        mock_docker.return_value = mock_client

        service = DockerService()
        service.create_volume("my-volume")

        mock_client.volumes.create.assert_called_with(name="my-volume")


# ============================================================================
# Integration with pytest
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
