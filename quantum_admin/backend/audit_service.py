"""
Audit Service for Quantum Admin
Centralized audit logging for all user actions
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)

try:
    from .models import AuditLog, Project
except ImportError:
    from models import AuditLog, Project


# Action types
class AuditAction:
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Deployment
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    PROMOTE = "promote"

    # Infrastructure
    START = "start"
    STOP = "stop"
    RESTART = "restart"

    # Configuration
    CONFIG_CHANGE = "config_change"
    SECRET_CHANGE = "secret_change"

    # Tests
    TEST_RUN = "test_run"
    TEST_COMPLETE = "test_complete"


def audit_log(
    db: Session,
    action: str,
    resource_type: str = None,
    resource_id: int = None,
    resource_name: str = None,
    user_id: str = None,
    user_ip: str = None,
    details: Dict[str, Any] = None,
    project_id: int = None,
    request_method: str = None,
    request_path: str = None
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        db: Database session
        action: The action performed (use AuditAction constants)
        resource_type: Type of resource affected (e.g., 'project', 'connector')
        resource_id: ID of the resource
        resource_name: Human-readable name of the resource
        user_id: User who performed the action
        user_ip: IP address of the user
        details: Additional details as dictionary
        project_id: Related project ID
        request_method: HTTP method used
        request_path: Request path

    Returns:
        The created AuditLog object
    """
    log_entry = AuditLog(
        timestamp=datetime.utcnow(),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        user_id=user_id,
        user_ip=user_ip,
        details=json.dumps(details) if details else None,
        project_id=project_id,
        request_method=request_method,
        request_path=request_path
    )

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    logger.info(f"Audit: {action} on {resource_type}:{resource_id} by {user_id}")
    return log_entry


def get_audit_logs(
    db: Session,
    project_id: int = None,
    action: str = None,
    resource_type: str = None,
    user_id: str = None,
    since: datetime = None,
    until: datetime = None,
    limit: int = 100,
    offset: int = 0
) -> List[AuditLog]:
    """
    Query audit logs with optional filters.

    Args:
        db: Database session
        project_id: Filter by project
        action: Filter by action type
        resource_type: Filter by resource type
        user_id: Filter by user
        since: Filter entries after this time
        until: Filter entries before this time
        limit: Maximum number of entries to return
        offset: Number of entries to skip

    Returns:
        List of AuditLog objects
    """
    query = db.query(AuditLog)

    if project_id:
        query = query.filter(AuditLog.project_id == project_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if since:
        query = query.filter(AuditLog.timestamp >= since)
    if until:
        query = query.filter(AuditLog.timestamp <= until)

    return query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()


def get_recent_activity(
    db: Session,
    limit: int = 10,
    project_id: int = None
) -> List[Dict]:
    """
    Get recent activity for dashboard display.

    Returns a formatted list of recent actions.
    """
    query = db.query(AuditLog)

    if project_id:
        query = query.filter(AuditLog.project_id == project_id)

    logs = query.order_by(desc(AuditLog.timestamp)).limit(limit).all()

    activities = []
    for log in logs:
        # Format the activity message
        if log.action == AuditAction.CREATE:
            message = f"Created {log.resource_type}: {log.resource_name}"
            icon = "plus"
            color = "success"
        elif log.action == AuditAction.UPDATE:
            message = f"Updated {log.resource_type}: {log.resource_name}"
            icon = "edit"
            color = "info"
        elif log.action == AuditAction.DELETE:
            message = f"Deleted {log.resource_type}: {log.resource_name}"
            icon = "trash"
            color = "danger"
        elif log.action == AuditAction.DEPLOY:
            message = f"Deployed {log.resource_name}"
            icon = "cloud-upload"
            color = "primary"
        elif log.action == AuditAction.ROLLBACK:
            message = f"Rolled back {log.resource_name}"
            icon = "rotate-ccw"
            color = "warning"
        elif log.action == AuditAction.LOGIN:
            message = f"User {log.user_id} logged in"
            icon = "log-in"
            color = "success"
        elif log.action == AuditAction.LOGOUT:
            message = f"User {log.user_id} logged out"
            icon = "log-out"
            color = "muted"
        elif log.action == AuditAction.START:
            message = f"Started {log.resource_type}: {log.resource_name}"
            icon = "play"
            color = "success"
        elif log.action == AuditAction.STOP:
            message = f"Stopped {log.resource_type}: {log.resource_name}"
            icon = "stop"
            color = "warning"
        elif log.action == AuditAction.TEST_RUN:
            message = f"Started test run for {log.resource_name}"
            icon = "check-circle"
            color = "info"
        else:
            message = f"{log.action.title()}: {log.resource_name or log.resource_type}"
            icon = "activity"
            color = "muted"

        activities.append({
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "message": message,
            "icon": icon,
            "color": color,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "project_id": log.project_id
        })

    return activities


def get_audit_stats(
    db: Session,
    project_id: int = None,
    days: int = 7
) -> Dict:
    """
    Get audit statistics for a time period.
    """
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(AuditLog).filter(AuditLog.timestamp >= since)

    if project_id:
        query = query.filter(AuditLog.project_id == project_id)

    total = query.count()

    # Count by action type
    action_counts = {}
    for action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE,
                   AuditAction.DEPLOY, AuditAction.LOGIN]:
        count = query.filter(AuditLog.action == action).count()
        action_counts[action] = count

    # Count by resource type
    resource_counts = db.query(
        AuditLog.resource_type,
        func.count(AuditLog.id)
    ).filter(AuditLog.timestamp >= since)

    if project_id:
        resource_counts = resource_counts.filter(AuditLog.project_id == project_id)

    resource_counts = resource_counts.group_by(AuditLog.resource_type).all()

    return {
        "total": total,
        "period_days": days,
        "by_action": action_counts,
        "by_resource": {r: c for r, c in resource_counts if r}
    }


class AuditService:
    """Service class for audit operations"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        resource_type: str = None,
        resource_id: int = None,
        resource_name: str = None,
        user_id: str = None,
        user_ip: str = None,
        details: Dict = None,
        project_id: int = None,
        request_method: str = None,
        request_path: str = None
    ) -> AuditLog:
        """Create an audit log entry"""
        return audit_log(
            self.db,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            user_id=user_id,
            user_ip=user_ip,
            details=details,
            project_id=project_id,
            request_method=request_method,
            request_path=request_path
        )

    def get_logs(
        self,
        project_id: int = None,
        action: str = None,
        resource_type: str = None,
        user_id: str = None,
        since: datetime = None,
        until: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Query audit logs"""
        return get_audit_logs(
            self.db,
            project_id=project_id,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
            since=since,
            until=until,
            limit=limit,
            offset=offset
        )

    def get_recent_activity(self, limit: int = 10, project_id: int = None) -> List[Dict]:
        """Get recent activity for dashboard"""
        return get_recent_activity(self.db, limit=limit, project_id=project_id)

    def get_stats(self, project_id: int = None, days: int = 7) -> Dict:
        """Get audit statistics"""
        return get_audit_stats(self.db, project_id=project_id, days=days)


def get_audit_service(db: Session) -> AuditService:
    """Get audit service instance"""
    return AuditService(db)
