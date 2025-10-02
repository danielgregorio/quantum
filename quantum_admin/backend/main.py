"""
Quantum Admin - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

try:
    # Try relative imports (when running as module)
    from . import crud, schemas
    from .database import get_db, init_db
    from .docker_service import DockerService
except ImportError:
    # Fall back to absolute imports (when running directly)
    import crud
    import schemas
    from database import get_db, init_db
    from docker_service import DockerService

# Create FastAPI app
app = FastAPI(
    title="Quantum Admin API",
    description="Administration interface for Quantum Language projects",
    version="1.0.0"
)

# Initialize Docker service (singleton)
docker_service = None

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database and Docker service on application startup"""
    global docker_service

    # Initialize database
    init_db()

    # Initialize Docker service
    try:
        docker_service = DockerService()
        print("[OK] Docker service initialized")
    except RuntimeError as e:
        print(f"[WARN] Docker service unavailable: {e}")
        print("[INFO] Datasource container management will be disabled")

    print("[OK] Quantum Admin API started successfully")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on application shutdown"""
    print("[INFO] Quantum Admin API shutting down")


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Quantum Admin API",
        "version": "1.0.0"
    }


# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@app.get("/projects", response_model=List[schemas.ProjectResponse], tags=["Projects"])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all projects"""
    projects = crud.get_projects(db, skip=skip, limit=limit)
    return projects


@app.post(
    "/projects",
    response_model=schemas.ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"]
)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db)
):
    """Create a new project"""
    try:
        new_project = crud.create_project(
            db,
            name=project.name,
            description=project.description or ""
        )
        return new_project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/projects/{project_id}", response_model=schemas.ProjectDetailResponse, tags=["Projects"])
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get a single project with all related data"""
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return project


@app.put("/projects/{project_id}", response_model=schemas.ProjectResponse, tags=["Projects"])
def update_project(
    project_id: int,
    project: schemas.ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a project"""
    updated_project = crud.update_project(
        db,
        project_id,
        name=project.name,
        description=project.description,
        status=project.status
    )
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return updated_project


@app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Projects"])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project"""
    success = crud.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    return None


# ============================================================================
# DATASOURCE ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/datasources", response_model=List[schemas.DatasourceResponse], tags=["Datasources"])
def list_datasources(project_id: int, db: Session = Depends(get_db)):
    """Get all datasources for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    datasources = crud.get_datasources(db, project_id)
    return datasources


@app.post(
    "/projects/{project_id}/datasources",
    response_model=schemas.DatasourceResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Datasources"]
)
def create_datasource(
    project_id: int,
    datasource: schemas.DatasourceCreate,
    db: Session = Depends(get_db)
):
    """Create a new datasource and optionally create Docker container"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Check if Docker is required but unavailable
    if datasource.connection_type == "docker" and docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available. Please ensure Docker Desktop is running."
        )

    try:
        container_id = None

        # Create Docker container if connection_type is "docker"
        if datasource.connection_type == "docker":
            # Prepare environment variables for database
            env_vars = {}
            if datasource.type == "postgres":
                env_vars = {
                    "POSTGRES_DB": datasource.database_name,
                    "POSTGRES_USER": datasource.username,
                    "POSTGRES_PASSWORD": datasource.password
                }
            elif datasource.type in ["mysql", "mariadb"]:
                env_vars = {
                    "MYSQL_DATABASE": datasource.database_name,
                    "MYSQL_USER": datasource.username,
                    "MYSQL_PASSWORD": datasource.password,
                    "MYSQL_ROOT_PASSWORD": datasource.password  # For initial setup
                }
            elif datasource.type == "mongodb":
                env_vars = {
                    "MONGO_INITDB_DATABASE": datasource.database_name,
                    "MONGO_INITDB_ROOT_USERNAME": datasource.username,
                    "MONGO_INITDB_ROOT_PASSWORD": datasource.password
                }

            # Create container
            container_name = f"{project.name}_{datasource.name}".replace(" ", "_").lower()
            container_id = docker_service.create_container(
                name=container_name,
                image=datasource.image,
                port=datasource.port,
                env_vars=env_vars,
                auto_start=datasource.auto_start
            )

            if not container_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create Docker container"
                )

        # TODO: Encrypt password before storing
        new_datasource = crud.create_datasource(
            db,
            project_id=project_id,
            name=datasource.name,
            type=datasource.type,
            connection_type=datasource.connection_type,
            container_id=container_id,
            image=datasource.image,
            port=datasource.port,
            host=datasource.host if datasource.connection_type == "direct" else "localhost",
            database_name=datasource.database_name,
            username=datasource.username,
            password_encrypted=datasource.password,  # TODO: Encrypt this
            auto_start=datasource.auto_start
        )
        return new_datasource
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# COMPONENT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/components", response_model=List[schemas.ComponentResponse], tags=["Components"])
def list_components(project_id: int, db: Session = Depends(get_db)):
    """Get all components for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    components = crud.get_components(db, project_id)
    return components


# ============================================================================
# DOCKER CONTAINER MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/datasources/{datasource_id}/start", tags=["Docker"])
def start_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Start a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Start container
    success = docker_service.start_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start container"
        )

    # Update status
    datasource.status = "running"
    db.commit()

    return {"message": "Container started successfully", "container_id": datasource.container_id}


@app.post("/datasources/{datasource_id}/stop", tags=["Docker"])
def stop_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Stop a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Stop container
    success = docker_service.stop_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop container"
        )

    # Update status
    datasource.status = "stopped"
    db.commit()

    return {"message": "Container stopped successfully", "container_id": datasource.container_id}


@app.post("/datasources/{datasource_id}/restart", tags=["Docker"])
def restart_datasource_container(datasource_id: int, db: Session = Depends(get_db)):
    """Restart a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Restart container
    success = docker_service.restart_container(datasource.container_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart container"
        )

    # Update status
    datasource.status = "running"
    db.commit()

    return {"message": "Container restarted successfully", "container_id": datasource.container_id}


@app.get("/datasources/{datasource_id}/status", tags=["Docker"])
def get_datasource_container_status(datasource_id: int, db: Session = Depends(get_db)):
    """Get detailed status of a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Get container status
    status_info = docker_service.get_container_status(datasource.container_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in Docker"
        )

    return status_info


@app.get("/datasources/{datasource_id}/logs", tags=["Docker"])
def get_datasource_container_logs(
    datasource_id: int,
    lines: int = 100,
    db: Session = Depends(get_db)
):
    """Get logs from a datasource's Docker container"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    if datasource.connection_type != "docker":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This datasource is not managed by Docker"
        )

    if not datasource.container_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No container associated with this datasource"
        )

    # Get container logs
    logs = docker_service.get_container_logs(datasource.container_id, lines=lines)
    if logs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found in Docker"
        )

    return {"logs": logs, "lines": lines}


@app.get("/docker/containers", tags=["Docker"])
def list_all_containers(all: bool = False):
    """List all Docker containers (optionally including stopped ones)"""
    if docker_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Docker service is not available"
        )

    containers = docker_service.list_containers(all=all)
    return {"containers": containers, "count": len(containers)}


# ============================================================================
# ENDPOINT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/endpoints", response_model=List[schemas.EndpointResponse], tags=["Endpoints"])
def list_endpoints(project_id: int, db: Session = Depends(get_db)):
    """Get all API endpoints for a project"""
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    endpoints = crud.get_endpoints(db, project_id)
    return endpoints


# ============================================================================
# RUN SERVER (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
