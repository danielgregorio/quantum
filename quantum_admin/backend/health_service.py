"""
Health Check Service for Quantum Admin
Monitors application health and creates incidents
"""
import asyncio
import logging
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)

try:
    from .models import HealthCheck, Incident, Project, Environment
except ImportError:
    from models import HealthCheck, Incident, Project, Environment


class HealthStatus:
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


def create_health_check(
    db: Session,
    name: str,
    endpoint: str,
    project_id: int = None,
    environment_id: int = None,
    method: str = "GET",
    expected_status: int = 200,
    timeout_seconds: int = 30,
    interval_seconds: int = 60
) -> HealthCheck:
    """Create a new health check configuration."""
    check = HealthCheck(
        name=name,
        endpoint=endpoint,
        project_id=project_id,
        environment_id=environment_id,
        method=method,
        expected_status=expected_status,
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds,
        is_active=True,
        last_status=HealthStatus.UNKNOWN,
        consecutive_failures=0
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def get_health_checks(
    db: Session,
    project_id: int = None,
    environment_id: int = None,
    active_only: bool = True
) -> List[HealthCheck]:
    """Get health checks with optional filters."""
    query = db.query(HealthCheck)

    if project_id:
        query = query.filter(HealthCheck.project_id == project_id)
    if environment_id:
        query = query.filter(HealthCheck.environment_id == environment_id)
    if active_only:
        query = query.filter(HealthCheck.is_active == True)

    return query.order_by(HealthCheck.name).all()


async def run_health_check(
    db: Session,
    check: HealthCheck
) -> Dict[str, Any]:
    """
    Execute a single health check and update its status.

    Returns:
        Dict with check results
    """
    result = {
        "check_id": check.id,
        "name": check.name,
        "endpoint": check.endpoint,
        "started_at": datetime.utcnow().isoformat()
    }

    try:
        async with httpx.AsyncClient(timeout=check.timeout_seconds) as client:
            start_time = datetime.utcnow()

            if check.method.upper() == "GET":
                response = await client.get(check.endpoint)
            elif check.method.upper() == "POST":
                response = await client.post(check.endpoint)
            elif check.method.upper() == "HEAD":
                response = await client.head(check.endpoint)
            else:
                response = await client.get(check.endpoint)

            response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            is_healthy = response.status_code == check.expected_status

            # Update check status
            previous_status = check.last_status
            check.last_check = datetime.utcnow()
            check.last_status = HealthStatus.HEALTHY if is_healthy else HealthStatus.UNHEALTHY

            if is_healthy:
                check.consecutive_failures = 0

                # Resolve any active incident
                active_incident = db.query(Incident).filter(
                    Incident.health_check_id == check.id,
                    Incident.status == "active"
                ).first()
                if active_incident:
                    active_incident.resolved_at = datetime.utcnow()
                    active_incident.status = "resolved"
                    active_incident.resolution_notes = "Automatic resolution - check passed"
            else:
                check.consecutive_failures += 1

                # Create incident if threshold reached
                if check.consecutive_failures >= 3:
                    create_incident(
                        db,
                        health_check_id=check.id,
                        project_id=check.project_id,
                        error_message=f"Health check failed: expected {check.expected_status}, got {response.status_code}",
                        error_code=response.status_code,
                        response_time_ms=response_time_ms
                    )

            db.commit()

            result.update({
                "status": check.last_status,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "is_healthy": is_healthy,
                "consecutive_failures": check.consecutive_failures
            })

    except httpx.TimeoutException:
        check.last_check = datetime.utcnow()
        check.last_status = HealthStatus.UNHEALTHY
        check.consecutive_failures += 1
        db.commit()

        result.update({
            "status": HealthStatus.UNHEALTHY,
            "error": "Timeout",
            "is_healthy": False,
            "consecutive_failures": check.consecutive_failures
        })

        if check.consecutive_failures >= 3:
            create_incident(
                db,
                health_check_id=check.id,
                project_id=check.project_id,
                error_message="Health check timeout",
                error_code=0,
                response_time_ms=check.timeout_seconds * 1000
            )

    except Exception as e:
        check.last_check = datetime.utcnow()
        check.last_status = HealthStatus.UNHEALTHY
        check.consecutive_failures += 1
        db.commit()

        result.update({
            "status": HealthStatus.UNHEALTHY,
            "error": str(e),
            "is_healthy": False,
            "consecutive_failures": check.consecutive_failures
        })

        logger.error(f"Health check {check.name} failed: {e}")

    return result


def create_incident(
    db: Session,
    health_check_id: int,
    project_id: int = None,
    error_message: str = None,
    error_code: int = None,
    response_time_ms: int = None
) -> Optional[Incident]:
    """Create a new incident for a health check failure."""
    # Check if there's already an active incident
    existing = db.query(Incident).filter(
        Incident.health_check_id == health_check_id,
        Incident.status == "active"
    ).first()

    if existing:
        return existing  # Don't create duplicate incidents

    incident = Incident(
        health_check_id=health_check_id,
        project_id=project_id,
        started_at=datetime.utcnow(),
        status="active",
        error_message=error_message,
        error_code=error_code,
        response_time_ms=response_time_ms
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    logger.warning(f"Incident created for health check {health_check_id}: {error_message}")
    return incident


def get_incidents(
    db: Session,
    project_id: int = None,
    status: str = None,
    limit: int = 50
) -> List[Incident]:
    """Get incidents with optional filters."""
    query = db.query(Incident)

    if project_id:
        query = query.filter(Incident.project_id == project_id)
    if status:
        query = query.filter(Incident.status == status)

    return query.order_by(desc(Incident.started_at)).limit(limit).all()


def resolve_incident(
    db: Session,
    incident_id: int,
    resolved_by: str = None,
    resolution_notes: str = None
) -> Optional[Incident]:
    """Manually resolve an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None

    incident.resolved_at = datetime.utcnow()
    incident.status = "resolved"
    incident.resolved_by = resolved_by
    incident.resolution_notes = resolution_notes
    db.commit()
    db.refresh(incident)

    return incident


def acknowledge_incident(
    db: Session,
    incident_id: int,
    acknowledged_by: str
) -> Optional[Incident]:
    """Acknowledge an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None

    incident.status = "acknowledged"
    incident.resolved_by = acknowledged_by
    db.commit()
    db.refresh(incident)

    return incident


def get_system_health_summary(db: Session) -> Dict:
    """Get overall system health summary."""
    checks = get_health_checks(db, active_only=True)
    incidents = get_incidents(db, status="active")

    healthy_count = sum(1 for c in checks if c.last_status == HealthStatus.HEALTHY)
    unhealthy_count = sum(1 for c in checks if c.last_status == HealthStatus.UNHEALTHY)
    unknown_count = sum(1 for c in checks if c.last_status == HealthStatus.UNKNOWN)

    # Overall status
    if unhealthy_count > 0:
        overall_status = HealthStatus.UNHEALTHY
    elif unknown_count > 0:
        overall_status = HealthStatus.DEGRADED
    else:
        overall_status = HealthStatus.HEALTHY

    return {
        "overall_status": overall_status,
        "total_checks": len(checks),
        "healthy": healthy_count,
        "unhealthy": unhealthy_count,
        "unknown": unknown_count,
        "active_incidents": len(incidents),
        "last_updated": datetime.utcnow().isoformat()
    }


class HealthService:
    """Service class for health check operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_check(
        self,
        name: str,
        endpoint: str,
        project_id: int = None,
        environment_id: int = None,
        **kwargs
    ) -> HealthCheck:
        return create_health_check(
            self.db,
            name=name,
            endpoint=endpoint,
            project_id=project_id,
            environment_id=environment_id,
            **kwargs
        )

    def get_checks(
        self,
        project_id: int = None,
        environment_id: int = None,
        active_only: bool = True
    ) -> List[HealthCheck]:
        return get_health_checks(
            self.db,
            project_id=project_id,
            environment_id=environment_id,
            active_only=active_only
        )

    async def run_check(self, check: HealthCheck) -> Dict:
        return await run_health_check(self.db, check)

    async def run_all_checks(self, project_id: int = None) -> List[Dict]:
        """Run all active health checks."""
        checks = self.get_checks(project_id=project_id)
        results = []
        for check in checks:
            result = await self.run_check(check)
            results.append(result)
        return results

    def get_incidents(
        self,
        project_id: int = None,
        status: str = None,
        limit: int = 50
    ) -> List[Incident]:
        return get_incidents(self.db, project_id=project_id, status=status, limit=limit)

    def resolve_incident(
        self,
        incident_id: int,
        resolved_by: str = None,
        resolution_notes: str = None
    ) -> Optional[Incident]:
        return resolve_incident(
            self.db,
            incident_id=incident_id,
            resolved_by=resolved_by,
            resolution_notes=resolution_notes
        )

    def acknowledge_incident(self, incident_id: int, acknowledged_by: str) -> Optional[Incident]:
        return acknowledge_incident(self.db, incident_id=incident_id, acknowledged_by=acknowledged_by)

    def get_summary(self) -> Dict:
        return get_system_health_summary(self.db)


def get_health_service(db: Session) -> HealthService:
    """Get health service instance."""
    return HealthService(db)
