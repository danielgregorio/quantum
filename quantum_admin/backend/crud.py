"""
CRUD operations for Quantum Admin
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime

from . import models


# ============================================================================
# PROJECT OPERATIONS
# ============================================================================

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[models.Project]:
    """Get all projects with pagination"""
    return db.query(models.Project).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    """Get a single project by ID"""
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_project_by_name(db: Session, name: str) -> Optional[models.Project]:
    """Get a project by name"""
    return db.query(models.Project).filter(models.Project.name == name).first()


def create_project(db: Session, name: str, description: str = "") -> models.Project:
    """Create a new project"""
    project = models.Project(name=name, description=description)
    db.add(project)
    try:
        db.commit()
        db.refresh(project)
        return project
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Project with name '{name}' already exists")


def update_project(
    db: Session,
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
) -> Optional[models.Project]:
    """Update an existing project"""
    project = get_project(db, project_id)
    if not project:
        return None

    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if status is not None:
        project.status = status

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project and all its related data"""
    project = get_project(db, project_id)
    if not project:
        return False

    db.delete(project)
    db.commit()
    return True


# ============================================================================
# DATASOURCE OPERATIONS
# ============================================================================

def get_datasources(db: Session, project_id: int) -> List[models.Datasource]:
    """Get all datasources for a project"""
    return db.query(models.Datasource).filter(
        models.Datasource.project_id == project_id
    ).all()


def get_datasource(db: Session, datasource_id: int) -> Optional[models.Datasource]:
    """Get a single datasource by ID"""
    return db.query(models.Datasource).filter(
        models.Datasource.id == datasource_id
    ).first()


def create_datasource(
    db: Session,
    project_id: int,
    name: str,
    type: str,
    connection_type: str,
    **kwargs
) -> models.Datasource:
    """Create a new datasource"""
    datasource = models.Datasource(
        project_id=project_id,
        name=name,
        type=type,
        connection_type=connection_type,
        **kwargs
    )
    db.add(datasource)
    try:
        db.commit()
        db.refresh(datasource)
        return datasource
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Datasource with name '{name}' already exists in this project")


def update_datasource(
    db: Session,
    datasource_id: int,
    **kwargs
) -> Optional[models.Datasource]:
    """Update a datasource"""
    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return None

    for key, value in kwargs.items():
        if hasattr(datasource, key) and value is not None:
            setattr(datasource, key, value)

    datasource.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(datasource)
    return datasource


def delete_datasource(db: Session, datasource_id: int) -> bool:
    """Delete a datasource"""
    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return False

    db.delete(datasource)
    db.commit()
    return True


# ============================================================================
# COMPONENT OPERATIONS
# ============================================================================

def get_components(db: Session, project_id: int) -> List[models.Component]:
    """Get all components for a project"""
    return db.query(models.Component).filter(
        models.Component.project_id == project_id
    ).all()


def get_component(db: Session, component_id: int) -> Optional[models.Component]:
    """Get a single component by ID"""
    return db.query(models.Component).filter(
        models.Component.id == component_id
    ).first()


def create_or_update_component(
    db: Session,
    project_id: int,
    name: str,
    file_path: str,
    status: str = "unknown",
    error_message: Optional[str] = None
) -> models.Component:
    """Create or update a component (upsert)"""
    component = db.query(models.Component).filter(
        models.Component.project_id == project_id,
        models.Component.name == name
    ).first()

    if component:
        # Update existing
        component.file_path = file_path
        component.status = status
        component.error_message = error_message
        component.last_compiled = datetime.utcnow()
    else:
        # Create new
        component = models.Component(
            project_id=project_id,
            name=name,
            file_path=file_path,
            status=status,
            error_message=error_message,
            last_compiled=datetime.utcnow()
        )
        db.add(component)

    db.commit()
    db.refresh(component)
    return component


# ============================================================================
# ENDPOINT OPERATIONS
# ============================================================================

def get_endpoints(db: Session, project_id: int) -> List[models.Endpoint]:
    """Get all endpoints for a project"""
    return db.query(models.Endpoint).filter(
        models.Endpoint.project_id == project_id
    ).all()


def create_or_update_endpoint(
    db: Session,
    project_id: int,
    method: str,
    path: str,
    function_name: str,
    component_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.Endpoint:
    """Create or update an endpoint (upsert)"""
    endpoint = db.query(models.Endpoint).filter(
        models.Endpoint.project_id == project_id,
        models.Endpoint.method == method,
        models.Endpoint.path == path
    ).first()

    if endpoint:
        # Update existing
        endpoint.function_name = function_name
        endpoint.component_id = component_id
        endpoint.description = description
    else:
        # Create new
        endpoint = models.Endpoint(
            project_id=project_id,
            method=method,
            path=path,
            function_name=function_name,
            component_id=component_id,
            description=description
        )
        db.add(endpoint)

    db.commit()
    db.refresh(endpoint)
    return endpoint
