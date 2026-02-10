"""
Resource Manager for Quantum Admin
Centralized management of ports, secrets, services, and configs
"""
import os
import json
import socket
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

try:
    from .models import PortAllocation, PortRange, Secret, ServiceRegistry, Project, Environment
    from .database import SessionLocal
except ImportError:
    from models import PortAllocation, PortRange, Secret, ServiceRegistry, Project, Environment
    from database import SessionLocal


class ResourceExhaustedError(Exception):
    """Raised when no resources are available"""
    pass


class PortManager:
    """Manages port allocation and tracking"""

    DEFAULT_RANGES = {
        "app": (8000, 8999),
        "database": (5400, 5499),
        "cache": (6370, 6399),
        "web": (3000, 3099),
        "queue": (5670, 5699),
    }

    def __init__(self, db: Session):
        self.db = db
        self._ensure_default_ranges()

    def _ensure_default_ranges(self):
        """Create default port ranges if they don't exist"""
        for name, (start, end) in self.DEFAULT_RANGES.items():
            existing = self.db.query(PortRange).filter(PortRange.name == name).first()
            if not existing:
                range_obj = PortRange(
                    name=name,
                    start_port=start,
                    end_port=end,
                    host='*',
                    description=f"Default range for {name} services"
                )
                self.db.add(range_obj)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def allocate(
        self,
        service_name: str,
        port_type: str = "app",
        host: str = "localhost",
        project_id: int = None,
        environment_id: int = None,
        preferred_port: int = None
    ) -> Optional[PortAllocation]:
        """
        Allocate an available port for a service.

        Returns the PortAllocation object, or None if no ports available.
        """
        # Check if already allocated
        existing = self.db.query(PortAllocation).filter(
            PortAllocation.service_name == service_name,
            PortAllocation.host == host,
            PortAllocation.status != 'released'
        ).first()
        if existing:
            logger.info(f"Port already allocated for {service_name}@{host}: {existing.port}")
            return existing

        # Try preferred port first
        if preferred_port and self.is_available(preferred_port, host):
            return self._do_allocate(
                service_name, preferred_port, port_type, host,
                project_id, environment_id
            )

        # Find next available in range
        range_obj = self._get_range(port_type, host)
        if not range_obj:
            logger.error(f"No port range defined for type '{port_type}'")
            return None

        for port in range(range_obj.start_port, range_obj.end_port + 1):
            if self.is_available(port, host):
                return self._do_allocate(
                    service_name, port, port_type, host,
                    project_id, environment_id
                )

        logger.error(f"No available ports in {port_type} range ({range_obj.start_port}-{range_obj.end_port}) for host {host}")
        return None

    def _do_allocate(
        self,
        service_name: str,
        port: int,
        port_type: str,
        host: str,
        project_id: int = None,
        environment_id: int = None
    ) -> PortAllocation:
        """Create the allocation record"""
        allocation = PortAllocation(
            service_name=service_name,
            port=port,
            port_type=port_type,
            host=host,
            project_id=project_id,
            environment_id=environment_id,
            status='allocated'
        )
        self.db.add(allocation)
        try:
            self.db.commit()
            logger.info(f"Allocated port {port} for {service_name}@{host}")
            return allocation
        except IntegrityError:
            self.db.rollback()
            raise ResourceExhaustedError(f"Port {port} on {host} is already in use")

    def release(self, port_or_service: int | str, host: str = "localhost") -> bool:
        """Release a port allocation by port number or service name"""
        if isinstance(port_or_service, int):
            # Release by port number
            allocation = self.db.query(PortAllocation).filter(
                PortAllocation.port == port_or_service,
                PortAllocation.host == host,
                PortAllocation.status != 'released'
            ).first()
        else:
            # Release by service name
            allocation = self.db.query(PortAllocation).filter(
                PortAllocation.service_name == port_or_service,
                PortAllocation.host == host,
                PortAllocation.status != 'released'
            ).first()

        if not allocation:
            return False

        allocation.status = 'released'
        allocation.released_at = datetime.utcnow()
        self.db.commit()
        logger.info(f"Released port {allocation.port}@{host}")
        return True

    def reserve(
        self,
        port: int,
        host: str,
        reason: str,
        service_name: str = None
    ) -> bool:
        """Reserve a specific port (prevents auto-allocation)"""
        # Check if already allocated
        existing = self.db.query(PortAllocation).filter(
            PortAllocation.port == port,
            PortAllocation.host == host,
            PortAllocation.status != 'released'
        ).first()

        if existing:
            if existing.is_reserved:
                return True  # Already reserved
            return False  # In use by another service

        # Create reservation
        allocation = PortAllocation(
            service_name=service_name or f"reserved-{port}",
            port=port,
            port_type='reserved',
            host=host,
            status='reserved',
            is_reserved=True,
            reserved_reason=reason
        )
        self.db.add(allocation)
        self.db.commit()
        logger.info(f"Reserved port {port}@{host}: {reason}")
        return True

    def get(self, service_name: str, host: str = "localhost") -> Optional[int]:
        """Get allocated port for a service"""
        allocation = self.db.query(PortAllocation).filter(
            PortAllocation.service_name == service_name,
            PortAllocation.host == host,
            PortAllocation.status != 'released'
        ).first()
        return allocation.port if allocation else None

    def is_available(self, port: int, host: str = "localhost") -> bool:
        """Check if port is available (not allocated and not in use)"""
        # Check database
        allocation = self.db.query(PortAllocation).filter(
            PortAllocation.port == port,
            PortAllocation.host == host,
            PortAllocation.status != 'released'
        ).first()

        if allocation:
            return False

        # Check if port is actually in use on localhost
        if host == 'localhost' or host == '127.0.0.1':
            return self._check_port_free_local(port)

        return True

    def _check_port_free_local(self, port: int) -> bool:
        """Check if local port is free using socket"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.settimeout(0.5)
                s.bind(('127.0.0.1', port))
                return True
            except OSError:
                return False

    def _get_range(self, port_type: str, host: str) -> Optional[PortRange]:
        """Get port range for a type"""
        # First try host-specific range
        range_obj = self.db.query(PortRange).filter(
            PortRange.name == port_type,
            PortRange.host == host
        ).first()

        if range_obj:
            return range_obj

        # Fall back to wildcard range
        return self.db.query(PortRange).filter(
            PortRange.name == port_type,
            PortRange.host == '*'
        ).first()

    def get_ranges(self) -> List[PortRange]:
        """Get all port ranges"""
        return self.db.query(PortRange).all()

    def set_range(
        self,
        name: str,
        start: int,
        end: int,
        host: str = "*",
        description: str = None
    ) -> PortRange:
        """Set or update a port range"""
        existing = self.db.query(PortRange).filter(
            PortRange.name == name,
            PortRange.host == host
        ).first()

        if existing:
            existing.start_port = start
            existing.end_port = end
            if description:
                existing.description = description
        else:
            existing = PortRange(
                name=name,
                start_port=start,
                end_port=end,
                host=host,
                description=description or f"Range for {name}"
            )
            self.db.add(existing)

        self.db.commit()
        return existing

    def create_range(
        self,
        name: str,
        start_port: int,
        end_port: int,
        host: str = "*",
        description: str = None
    ) -> PortRange:
        """Create a new port range (alias for set_range)"""
        return self.set_range(name, start_port, end_port, host, description)

    def list_allocations(
        self,
        host: str = None,
        project_id: int = None,
        environment_id: int = None,
        status: str = None,
        include_released: bool = False
    ) -> List[PortAllocation]:
        """List all port allocations with optional filters"""
        query = self.db.query(PortAllocation)

        if host:
            query = query.filter(PortAllocation.host == host)
        if project_id:
            query = query.filter(PortAllocation.project_id == project_id)
        if environment_id:
            query = query.filter(PortAllocation.environment_id == environment_id)
        if status:
            query = query.filter(PortAllocation.status == status)
        elif not include_released:
            query = query.filter(PortAllocation.status != 'released')

        return query.order_by(PortAllocation.port).all()

    def get_usage_stats(self, host: str = None) -> Dict[str, Dict]:
        """Get port usage statistics by range"""
        ranges = self.get_ranges()
        stats = {}

        for r in ranges:
            if host and r.host != '*' and r.host != host:
                continue

            total = r.end_port - r.start_port + 1
            used = self.db.query(PortAllocation).filter(
                PortAllocation.port >= r.start_port,
                PortAllocation.port <= r.end_port,
                PortAllocation.status != 'released'
            )
            if host:
                used = used.filter(PortAllocation.host == host)

            used_count = used.count()

            stats[r.name] = {
                "range": f"{r.start_port}-{r.end_port}",
                "total": total,
                "used": used_count,
                "available": total - used_count,
                "percent_available": round((total - used_count) / total * 100, 1)
            }

        return stats


class SecretManager:
    """Manages encrypted secrets"""

    def __init__(self, db: Session):
        self.db = db
        self._fernet = self._init_encryption()

    def _init_encryption(self) -> Fernet:
        """Initialize Fernet encryption with key from env or generate"""
        key = os.environ.get('QUANTUM_ENCRYPTION_KEY')
        if not key:
            # Generate a stable key from a passphrase (NOT SECURE for production)
            passphrase = os.environ.get('QUANTUM_SECRET_PASSPHRASE', 'quantum-admin-default-key')
            key = base64.urlsafe_b64encode(
                hashlib.sha256(passphrase.encode()).digest()
            )
            logger.warning("Using derived encryption key. Set QUANTUM_ENCRYPTION_KEY for production!")
        else:
            key = key.encode() if isinstance(key, str) else key

        return Fernet(key)

    def set(
        self,
        key: str,
        value: str,
        scope: str = "global",
        project_id: int = None,
        environment_id: int = None,
        description: str = None
    ) -> Secret:
        """Store an encrypted secret"""
        # Encrypt the value
        encrypted = self._fernet.encrypt(value.encode()).decode()

        # Check if exists
        existing = self.db.query(Secret).filter(
            Secret.key == key,
            Secret.project_id == project_id,
            Secret.environment_id == environment_id
        ).first()

        if existing:
            existing.encrypted_value = encrypted
            existing.updated_at = datetime.utcnow()
            if description:
                existing.description = description
        else:
            existing = Secret(
                key=key,
                encrypted_value=encrypted,
                scope=scope,
                project_id=project_id,
                environment_id=environment_id,
                description=description
            )
            self.db.add(existing)

        self.db.commit()
        logger.info(f"Secret '{key}' stored (scope={scope})")
        return existing

    def get(
        self,
        key: str,
        project_id: int = None,
        environment_id: int = None
    ) -> Optional[str]:
        """Retrieve and decrypt a secret"""
        # Try environment-specific first
        if environment_id:
            secret = self.db.query(Secret).filter(
                Secret.key == key,
                Secret.environment_id == environment_id
            ).first()
            if secret:
                return self._decrypt(secret.encrypted_value)

        # Try project-specific
        if project_id:
            secret = self.db.query(Secret).filter(
                Secret.key == key,
                Secret.project_id == project_id,
                Secret.environment_id == None
            ).first()
            if secret:
                return self._decrypt(secret.encrypted_value)

        # Try global
        secret = self.db.query(Secret).filter(
            Secret.key == key,
            Secret.project_id == None,
            Secret.environment_id == None
        ).first()
        if secret:
            return self._decrypt(secret.encrypted_value)

        return None

    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a value"""
        return self._fernet.decrypt(encrypted_value.encode()).decode()

    def list(
        self,
        project_id: int = None,
        environment_id: int = None,
        include_values: bool = False
    ) -> List[Dict]:
        """List secrets (optionally with decrypted values)"""
        query = self.db.query(Secret)

        if project_id is not None:
            query = query.filter(
                (Secret.project_id == project_id) | (Secret.project_id == None)
            )
        if environment_id is not None:
            query = query.filter(
                (Secret.environment_id == environment_id) | (Secret.environment_id == None)
            )

        secrets = query.order_by(Secret.scope, Secret.key).all()

        result = []
        for s in secrets:
            data = s.to_dict(include_value=False)
            if include_values:
                data['value'] = self._decrypt(s.encrypted_value)
            result.append(data)

        return result

    def list_secrets(
        self,
        project_id: int = None,
        environment_id: int = None,
        scope: str = None
    ) -> List[Secret]:
        """List secrets as Secret objects with optional filters"""
        query = self.db.query(Secret)

        if project_id is not None:
            query = query.filter(
                (Secret.project_id == project_id) | (Secret.project_id == None)
            )
        if environment_id is not None:
            query = query.filter(
                (Secret.environment_id == environment_id) | (Secret.environment_id == None)
            )
        if scope:
            query = query.filter(Secret.scope == scope)

        return query.order_by(Secret.scope, Secret.key).all()

    def delete(self, secret_id_or_key, project_id: int = None, environment_id: int = None) -> bool:
        """Delete a secret by id or key"""
        if isinstance(secret_id_or_key, int):
            # Delete by id
            secret = self.db.query(Secret).filter(Secret.id == secret_id_or_key).first()
        else:
            # Delete by key
            query = self.db.query(Secret).filter(Secret.key == secret_id_or_key)
            if project_id is not None:
                query = query.filter(Secret.project_id == project_id)
            if environment_id is not None:
                query = query.filter(Secret.environment_id == environment_id)
            secret = query.first()

        if secret:
            key = secret.key
            self.db.delete(secret)
            self.db.commit()
            logger.info(f"Secret '{key}' deleted")
            return True
        return False

    def rotate(
        self,
        secret_id_or_key,
        new_value: str,
        project_id: int = None,
        environment_id: int = None
    ) -> bool:
        """Rotate a secret value by id or key"""
        if isinstance(secret_id_or_key, int):
            # Find by id
            secret = self.db.query(Secret).filter(Secret.id == secret_id_or_key).first()
        else:
            # Find by key
            secret = self.db.query(Secret).filter(
                Secret.key == secret_id_or_key,
                Secret.project_id == project_id,
                Secret.environment_id == environment_id
            ).first()

        if not secret:
            return False

        secret.encrypted_value = self._fernet.encrypt(new_value.encode()).decode()
        secret.last_rotated = datetime.utcnow()
        secret.updated_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Secret '{key}' rotated")
        return True


class ServiceRegistryManager:
    """Manages service discovery registry"""

    def __init__(self, db: Session):
        self.db = db

    def register(
        self,
        name: str,
        host: str,
        port: int,
        service_type: str = "app",
        protocol: str = "http",
        health_endpoint: str = "/health",
        health_interval: int = 30,
        project_id: int = None,
        environment_id: int = None,
        metadata: Dict = None
    ) -> ServiceRegistry:
        """Register a service for discovery"""
        existing = self.db.query(ServiceRegistry).filter(
            ServiceRegistry.name == name
        ).first()

        if existing:
            existing.host = host
            existing.port = port
            existing.service_type = service_type
            existing.protocol = protocol
            existing.health_endpoint = health_endpoint
            existing.health_interval = health_interval
            existing.project_id = project_id
            existing.environment_id = environment_id
            existing.metadata_json = json.dumps(metadata) if metadata else None
            existing.updated_at = datetime.utcnow()
        else:
            existing = ServiceRegistry(
                name=name,
                host=host,
                port=port,
                service_type=service_type,
                protocol=protocol,
                health_endpoint=health_endpoint,
                health_interval=health_interval,
                project_id=project_id,
                environment_id=environment_id,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            self.db.add(existing)

        self.db.commit()
        logger.info(f"Service '{name}' registered at {protocol}://{host}:{port}")
        return existing

    def discover(
        self,
        service_type: str,
        project_id: int = None,
        environment_id: int = None,
        healthy_only: bool = True
    ) -> List[ServiceRegistry]:
        """Discover services by type"""
        query = self.db.query(ServiceRegistry).filter(
            ServiceRegistry.service_type == service_type
        )
        if project_id:
            query = query.filter(ServiceRegistry.project_id == project_id)
        if environment_id:
            query = query.filter(ServiceRegistry.environment_id == environment_id)
        if healthy_only:
            query = query.filter(ServiceRegistry.health_status == 'healthy')
        return query.all()

    def discover_by_name(self, name: str, healthy_only: bool = True) -> Optional[ServiceRegistry]:
        """Discover a service by name"""
        query = self.db.query(ServiceRegistry).filter(ServiceRegistry.name == name)
        if healthy_only:
            query = query.filter(ServiceRegistry.health_status == 'healthy')
        return query.first()

    def discover_by_type(
        self,
        service_type: str,
        project_id: int = None,
        healthy_only: bool = True
    ) -> List[ServiceRegistry]:
        """Discover all services of a type"""
        return self.discover(service_type, project_id, healthy_only=healthy_only)

    def deregister(self, name: str) -> bool:
        """Remove a service from registry by name"""
        service = self.db.query(ServiceRegistry).filter(
            ServiceRegistry.name == name
        ).first()
        if service:
            self.db.delete(service)
            self.db.commit()
            logger.info(f"Service '{name}' deregistered")
            return True
        return False

    def unregister(self, service_id: int) -> bool:
        """Remove a service from registry by id"""
        service = self.db.query(ServiceRegistry).filter(
            ServiceRegistry.id == service_id
        ).first()
        if service:
            name = service.name
            self.db.delete(service)
            self.db.commit()
            logger.info(f"Service '{name}' unregistered")
            return True
        return False

    def list_all(self) -> List[ServiceRegistry]:
        """List all registered services"""
        return self.db.query(ServiceRegistry).order_by(
            ServiceRegistry.service_type,
            ServiceRegistry.name
        ).all()

    def list_services(
        self,
        project_id: int = None,
        environment_id: int = None,
        service_type: str = None,
        healthy_only: bool = False
    ) -> List[ServiceRegistry]:
        """List services with optional filters"""
        query = self.db.query(ServiceRegistry)

        if project_id:
            query = query.filter(ServiceRegistry.project_id == project_id)
        if environment_id:
            query = query.filter(ServiceRegistry.environment_id == environment_id)
        if service_type:
            query = query.filter(ServiceRegistry.service_type == service_type)
        if healthy_only:
            query = query.filter(ServiceRegistry.health_status == 'healthy')

        return query.order_by(ServiceRegistry.service_type, ServiceRegistry.name).all()

    async def check_health(self, service_id: int) -> Dict:
        """Check health of a service by id and return result dict"""
        import httpx
        import time

        service = self.db.query(ServiceRegistry).filter(
            ServiceRegistry.id == service_id
        ).first()

        if not service:
            return {"status": "error", "message": "Service not found"}

        if not service.health_endpoint:
            return {"status": "unknown", "message": "No health endpoint configured"}

        url = f"{service.protocol}://{service.host}:{service.port}{service.health_endpoint}"

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                response_time = int((time.time() - start_time) * 1000)
                is_healthy = response.status_code == 200

                service.health_status = 'healthy' if is_healthy else 'unhealthy'
                service.last_health_check = datetime.utcnow()
                service.consecutive_failures = 0 if is_healthy else service.consecutive_failures + 1
                self.db.commit()

                return {
                    "status": service.health_status,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "url": url
                }
        except Exception as e:
            service.health_status = 'unhealthy'
            service.last_health_check = datetime.utcnow()
            service.consecutive_failures += 1
            self.db.commit()
            logger.warning(f"Health check failed for {service.name}: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": url
            }

    async def _health_check_service(self, service: ServiceRegistry) -> bool:
        """Internal: Check health of a single service"""
        import httpx

        if not service.health_endpoint:
            return True  # No health check configured

        url = f"{service.protocol}://{service.host}:{service.port}{service.health_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                is_healthy = response.status_code == 200

                service.health_status = 'healthy' if is_healthy else 'unhealthy'
                service.last_health_check = datetime.utcnow()
                service.consecutive_failures = 0 if is_healthy else service.consecutive_failures + 1
                self.db.commit()

                return is_healthy
        except Exception as e:
            service.health_status = 'unhealthy'
            service.last_health_check = datetime.utcnow()
            service.consecutive_failures += 1
            self.db.commit()
            logger.warning(f"Health check failed for {service.name}: {e}")
            return False

    async def run_health_checks(
        self,
        project_id: int = None,
        environment_id: int = None
    ) -> List[Dict]:
        """Run health checks on services with optional filters"""
        services = self.list_services(
            project_id=project_id,
            environment_id=environment_id
        )
        results = []

        for service in services:
            is_healthy = await self._health_check_service(service)
            results.append({
                "name": service.name,
                "healthy": is_healthy,
                "status": service.health_status,
                "url": f"{service.protocol}://{service.host}:{service.port}{service.health_endpoint}",
                "last_check": service.last_health_check.isoformat() if service.last_health_check else None
            })

        return results

    async def health_check_all(self) -> Dict[str, Dict]:
        """Run health checks on all registered services"""
        services = self.list_all()
        results = {}

        for service in services:
            is_healthy = await self._health_check_service(service)
            results[service.name] = {
                "healthy": is_healthy,
                "status": service.health_status,
                "url": f"{service.protocol}://{service.host}:{service.port}{service.health_endpoint}",
                "last_check": service.last_health_check.isoformat() if service.last_health_check else None,
                "failures": service.consecutive_failures
            }

        return results


class ResourceDiscovery:
    """Auto-discovery of system resources"""

    def __init__(self):
        self._psutil_available = False
        try:
            import psutil
            self._psutil_available = True
        except ImportError:
            logger.warning("psutil not installed - limited resource discovery")

    def scan_ports_in_use(self, host: str = "localhost") -> List[Dict]:
        """Scan for ports currently in use on the system"""
        if not self._psutil_available:
            return self._scan_ports_socket(host)

        import psutil
        ports = []

        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr:
                port_info = {
                    "port": conn.laddr.port,
                    "host": conn.laddr.ip or "0.0.0.0",
                    "pid": conn.pid,
                    "status": conn.status
                }

                # Try to get process name
                if conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        port_info["process_name"] = proc.name()
                        port_info["process_cmdline"] = " ".join(proc.cmdline()[:3])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                ports.append(port_info)

        return sorted(ports, key=lambda x: x["port"])

    def _scan_ports_socket(self, host: str, port_range: tuple = (1, 10000)) -> List[Dict]:
        """Fallback port scanning using sockets (slower)"""
        ports = []
        for port in range(port_range[0], min(port_range[1], 10000)):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex((host, port))
                if result == 0:
                    ports.append({
                        "port": port,
                        "host": host,
                        "status": "LISTEN"
                    })
        return ports

    def detect_quantum_processes(self) -> List[Dict]:
        """Detect running Quantum framework processes"""
        if not self._psutil_available:
            return []

        import psutil
        quantum_procs = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('quantum' in str(arg).lower() for arg in cmdline):
                    quantum_procs.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": " ".join(cmdline[:5]),
                        "started": datetime.fromtimestamp(proc.info['create_time']).isoformat()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return quantum_procs

    def get_docker_containers(self, docker_client=None) -> List[Dict]:
        """List Docker containers if available"""
        containers = []

        try:
            import docker
            client = docker_client or docker.from_env()

            for container in client.containers.list(all=True):
                ports = {}
                if container.ports:
                    for internal, external in container.ports.items():
                        if external:
                            ports[internal] = external[0]['HostPort'] if external else None

                containers.append({
                    "id": container.short_id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "status": container.status,
                    "ports": ports,
                    "created": container.attrs.get('Created', '')[:19]
                })
        except ImportError:
            logger.warning("Docker SDK not installed")
        except Exception as e:
            logger.warning(f"Docker not available: {e}")

        return containers

    def get_system_resources(self) -> Dict:
        """Get system resource usage"""
        if not self._psutil_available:
            return {"available": False}

        import psutil

        return {
            "available": True,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "cpu_count": psutil.cpu_count(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }

    def get_overview(self, docker_client=None) -> Dict:
        """Get complete resource overview"""
        return {
            "ports_in_use": self.scan_ports_in_use(),
            "quantum_processes": self.detect_quantum_processes(),
            "docker_containers": self.get_docker_containers(docker_client),
            "system": self.get_system_resources(),
            "scanned_at": datetime.utcnow().isoformat()
        }


class ResourceManager:
    """Centralized resource management service"""

    def __init__(self, db: Session):
        self.db = db
        self.port_manager = PortManager(db)
        self.secret_manager = SecretManager(db)
        self.service_registry = ServiceRegistryManager(db)
        self.discovery = ResourceDiscovery()

    # Property aliases for API convenience
    @property
    def ports(self) -> PortManager:
        return self.port_manager

    @property
    def secrets(self) -> SecretManager:
        return self.secret_manager

    @property
    def services(self) -> 'ServiceRegistryManager':
        return self.service_registry

    # Port Management
    def allocate_port(self, *args, **kwargs) -> int:
        return self.port_manager.allocate(*args, **kwargs)

    def release_port(self, *args, **kwargs) -> bool:
        return self.port_manager.release(*args, **kwargs)

    def reserve_port(self, *args, **kwargs) -> bool:
        return self.port_manager.reserve(*args, **kwargs)

    def get_port(self, *args, **kwargs) -> Optional[int]:
        return self.port_manager.get(*args, **kwargs)

    def list_allocations(self, *args, **kwargs) -> List[PortAllocation]:
        return self.port_manager.list_allocations(*args, **kwargs)

    def check_port_available(self, port: int, host: str = "localhost") -> bool:
        return self.port_manager.is_available(port, host)

    def get_port_ranges(self) -> List[PortRange]:
        return self.port_manager.get_ranges()

    def get_port_usage(self, host: str = None) -> Dict:
        return self.port_manager.get_usage_stats(host)

    # Secret Management
    def set_secret(self, *args, **kwargs) -> Secret:
        return self.secret_manager.set(*args, **kwargs)

    def get_secret(self, *args, **kwargs) -> Optional[str]:
        return self.secret_manager.get(*args, **kwargs)

    def list_secrets(self, *args, **kwargs) -> List[Dict]:
        return self.secret_manager.list(*args, **kwargs)

    def delete_secret(self, *args, **kwargs) -> bool:
        return self.secret_manager.delete(*args, **kwargs)

    def rotate_secret(self, *args, **kwargs) -> bool:
        return self.secret_manager.rotate(*args, **kwargs)

    # Service Registry
    def register_service(self, *args, **kwargs) -> ServiceRegistry:
        return self.service_registry.register(*args, **kwargs)

    def discover(self, *args, **kwargs) -> Optional[ServiceRegistry]:
        return self.service_registry.discover(*args, **kwargs)

    def discover_by_type(self, *args, **kwargs) -> List[ServiceRegistry]:
        return self.service_registry.discover_by_type(*args, **kwargs)

    def deregister_service(self, name: str) -> bool:
        return self.service_registry.deregister(name)

    async def health_check_all(self) -> Dict[str, Dict]:
        return await self.service_registry.health_check_all()

    # Resource Discovery
    def scan_resources(self, docker_client=None) -> Dict:
        """Perform full resource scan"""
        return self.discovery.get_overview(docker_client)

    def scan_ports(self, host: str = "localhost") -> List[Dict]:
        """Scan ports in use"""
        return self.discovery.scan_ports_in_use(host)

    def scan_processes(self) -> List[Dict]:
        """Scan for Quantum processes"""
        return self.discovery.detect_quantum_processes()

    def scan_containers(self, docker_client=None) -> List[Dict]:
        """Scan Docker containers"""
        return self.discovery.get_docker_containers(docker_client)

    def get_system_resources(self) -> Dict:
        """Get system resource usage"""
        return self.discovery.get_system_resources()

    def sync_discovered_ports(self, docker_client=None) -> Dict:
        """
        Sync discovered ports with database allocations.
        This reconciles what's actually running with what's tracked.
        """
        discovered = self.discovery.scan_ports_in_use()
        allocations = self.port_manager.list_allocations(include_released=False)

        allocated_ports = {a.port: a for a in allocations}
        discovered_ports = {p['port']: p for p in discovered}

        # Find orphaned allocations (tracked but not running)
        orphaned = []
        for port, alloc in allocated_ports.items():
            if port not in discovered_ports:
                orphaned.append({
                    "port": port,
                    "service": alloc.service_name,
                    "status": "not_running"
                })

        # Find untracked ports (running but not allocated)
        untracked = []
        for port, info in discovered_ports.items():
            if port not in allocated_ports and 1024 < port < 65535:
                untracked.append({
                    "port": port,
                    "process": info.get("process_name", "unknown"),
                    "status": "untracked"
                })

        return {
            "tracked": len(allocations),
            "discovered": len(discovered),
            "orphaned": orphaned,
            "untracked": untracked[:50],  # Limit to 50
            "synced_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_resource_manager = None


def get_resource_manager(db: Session = None) -> ResourceManager:
    """Get resource manager instance"""
    if db:
        return ResourceManager(db)

    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager(SessionLocal())
    return _resource_manager
