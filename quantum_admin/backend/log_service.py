"""
Log Service for Quantum Admin
Unified logging for application, database, and access logs
"""
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

logger = logging.getLogger(__name__)

try:
    from .models import ApplicationLog, Project, Environment
except ImportError:
    from models import ApplicationLog, Project, Environment


class LogLevel:
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogSource:
    APP = "app"          # Application logs (stdout/stderr)
    DB = "db"            # Database query logs
    ACCESS = "access"    # HTTP access logs
    DEPLOY = "deploy"    # Deployment logs
    SYSTEM = "system"    # System/infrastructure logs


def create_log(
    db: Session,
    project_id: int,
    level: str,
    source: str,
    message: str,
    environment_id: int = None,
    component_name: str = None,
    function_name: str = None,
    line_number: int = None,
    request_id: str = None,
    request_method: str = None,
    request_path: str = None,
    response_status: int = None,
    response_time_ms: int = None,
    extra_data: Dict = None
) -> ApplicationLog:
    """
    Create a log entry.

    Args:
        db: Database session
        project_id: Project this log belongs to
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        source: Log source (app, db, access, deploy, system)
        message: Log message
        environment_id: Optional environment ID
        component_name: Optional component name
        function_name: Optional function name
        line_number: Optional line number
        request_id: Optional request ID for tracing
        request_method: Optional HTTP method
        request_path: Optional request path
        response_status: Optional HTTP status code
        response_time_ms: Optional response time in milliseconds
        extra_data: Optional additional data as dictionary

    Returns:
        The created ApplicationLog object
    """
    log_entry = ApplicationLog(
        project_id=project_id,
        environment_id=environment_id,
        timestamp=datetime.utcnow(),
        level=level,
        source=source,
        message=message,
        component_name=component_name,
        function_name=function_name,
        line_number=line_number,
        request_id=request_id,
        request_method=request_method,
        request_path=request_path,
        response_status=response_status,
        response_time_ms=response_time_ms,
        extra_data=json.dumps(extra_data) if extra_data else None
    )

    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry


def get_logs(
    db: Session,
    project_id: int,
    source: str = None,
    level: str = None,
    environment_id: int = None,
    search: str = None,
    since: datetime = None,
    until: datetime = None,
    limit: int = 100,
    offset: int = 0
) -> List[ApplicationLog]:
    """
    Query logs with optional filters.

    Args:
        db: Database session
        project_id: Filter by project
        source: Filter by source (app, db, access, deploy, system)
        level: Filter by log level
        environment_id: Filter by environment
        search: Search in message
        since: Filter entries after this time
        until: Filter entries before this time
        limit: Maximum number of entries to return
        offset: Number of entries to skip

    Returns:
        List of ApplicationLog objects
    """
    query = db.query(ApplicationLog).filter(ApplicationLog.project_id == project_id)

    if source and source != 'all':
        query = query.filter(ApplicationLog.source == source)
    if level:
        query = query.filter(ApplicationLog.level == level)
    if environment_id:
        query = query.filter(ApplicationLog.environment_id == environment_id)
    if search:
        query = query.filter(ApplicationLog.message.ilike(f'%{search}%'))
    if since:
        query = query.filter(ApplicationLog.timestamp >= since)
    if until:
        query = query.filter(ApplicationLog.timestamp <= until)

    return query.order_by(desc(ApplicationLog.timestamp)).offset(offset).limit(limit).all()


def get_log_stats(
    db: Session,
    project_id: int,
    hours: int = 24
) -> Dict:
    """
    Get log statistics for a project.
    """
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(ApplicationLog).filter(
        ApplicationLog.project_id == project_id,
        ApplicationLog.timestamp >= since
    )

    total = query.count()

    # Count by level
    level_counts = {}
    for level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]:
        count = query.filter(ApplicationLog.level == level).count()
        level_counts[level.lower()] = count

    # Count by source
    source_counts = {}
    for source in [LogSource.APP, LogSource.DB, LogSource.ACCESS, LogSource.DEPLOY, LogSource.SYSTEM]:
        count = query.filter(ApplicationLog.source == source).count()
        source_counts[source] = count

    # Error rate
    error_count = level_counts.get('error', 0) + level_counts.get('critical', 0)
    error_rate = (error_count / total * 100) if total > 0 else 0

    return {
        "total": total,
        "period_hours": hours,
        "by_level": level_counts,
        "by_source": source_counts,
        "error_rate": round(error_rate, 2)
    }


def format_log_for_display(log: ApplicationLog) -> Dict:
    """Format a log entry for display."""
    return {
        "id": log.id,
        "timestamp": log.timestamp.strftime('%H:%M:%S') if log.timestamp else '',
        "timestamp_full": log.timestamp.isoformat() if log.timestamp else '',
        "level": log.level,
        "source": log.source,
        "message": log.message[:200] if log.message else '',
        "full_message": log.message,
        "component": log.component_name,
        "function": log.function_name,
        "request": f"{log.request_method} {log.request_path}" if log.request_method else None,
        "status": log.response_status,
        "duration": f"{log.response_time_ms}ms" if log.response_time_ms else None
    }


class LogService:
    """Service class for log operations"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        project_id: int,
        level: str,
        source: str,
        message: str,
        **kwargs
    ) -> ApplicationLog:
        """Create a log entry"""
        return create_log(
            self.db,
            project_id=project_id,
            level=level,
            source=source,
            message=message,
            **kwargs
        )

    def info(self, project_id: int, source: str, message: str, **kwargs) -> ApplicationLog:
        return self.log(project_id, LogLevel.INFO, source, message, **kwargs)

    def warning(self, project_id: int, source: str, message: str, **kwargs) -> ApplicationLog:
        return self.log(project_id, LogLevel.WARNING, source, message, **kwargs)

    def error(self, project_id: int, source: str, message: str, **kwargs) -> ApplicationLog:
        return self.log(project_id, LogLevel.ERROR, source, message, **kwargs)

    def debug(self, project_id: int, source: str, message: str, **kwargs) -> ApplicationLog:
        return self.log(project_id, LogLevel.DEBUG, source, message, **kwargs)

    def access_log(
        self,
        project_id: int,
        method: str,
        path: str,
        status: int,
        duration_ms: int,
        **kwargs
    ) -> ApplicationLog:
        """Create an access log entry"""
        message = f"{method} {path} {status} {duration_ms}ms"
        return self.log(
            project_id,
            LogLevel.INFO if status < 400 else LogLevel.WARNING if status < 500 else LogLevel.ERROR,
            LogSource.ACCESS,
            message,
            request_method=method,
            request_path=path,
            response_status=status,
            response_time_ms=duration_ms,
            **kwargs
        )

    def query_log(
        self,
        project_id: int,
        query: str,
        duration_ms: int,
        **kwargs
    ) -> ApplicationLog:
        """Create a database query log entry"""
        message = f"Query executed in {duration_ms}ms: {query[:100]}..."
        return self.log(
            project_id,
            LogLevel.DEBUG,
            LogSource.DB,
            message,
            response_time_ms=duration_ms,
            **kwargs
        )

    def get_logs(
        self,
        project_id: int,
        source: str = None,
        level: str = None,
        environment_id: int = None,
        search: str = None,
        since: datetime = None,
        until: datetime = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApplicationLog]:
        """Query logs"""
        return get_logs(
            self.db,
            project_id=project_id,
            source=source,
            level=level,
            environment_id=environment_id,
            search=search,
            since=since,
            until=until,
            limit=limit,
            offset=offset
        )

    def get_stats(self, project_id: int, hours: int = 24) -> Dict:
        """Get log statistics"""
        return get_log_stats(self.db, project_id=project_id, hours=hours)

    def format_logs(self, logs: List[ApplicationLog]) -> List[Dict]:
        """Format logs for display"""
        return [format_log_for_display(log) for log in logs]


def get_log_service(db: Session) -> LogService:
    """Get log service instance"""
    return LogService(db)
