"""
Quantum Admin - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import os
import logging

logger = logging.getLogger(__name__)

try:
    # Try relative imports (when running as module)
    from . import crud, schemas, models
    from .database import get_db, init_db
    from .docker_service import DockerService
    from .db_setup_service import DatabaseSetupService
except ImportError:
    # Fall back to absolute imports (when running directly)
    import crud
    import schemas
    import models
    from database import get_db, init_db
    from docker_service import DockerService
    from db_setup_service import DatabaseSetupService

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

# Mount static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")


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
# ROOT & HEALTH CHECK
# ============================================================================

@app.get("/", tags=["Root"])
def root():
    """Redirect to admin UI"""
    return RedirectResponse(url="/frontend/index.html")


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




@app.get("/api/datasources/by-name/{name}", tags=["API"])
def get_datasource_by_name(name: str, db: Session = Depends(get_db)):
    """
    Get datasource configuration by name for runtime use
    
    This endpoint is used by Quantum runtime to fetch datasource configuration
    when executing q:query components.
    """
    # Find datasource by name across all projects
    datasource = db.query(models.Datasource).filter(
        models.Datasource.name == name
    ).first()
    
    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource '{name}' not found"
        )
    
    # Only return if status is 'running' and setup is 'ready'
    if datasource.status != 'running':
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datasource '{name}' is not running (status: {datasource.status})"
        )
    
    if datasource.setup_status != 'ready':
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datasource '{name}' is not ready (setup status: {datasource.setup_status})"
        )
    
    # Return datasource configuration for runtime use
    return {
        'name': datasource.name,
        'type': datasource.type,
        'host': datasource.host,
        'port': datasource.port,
        'database_name': datasource.database_name,
        'username': datasource.username,
        'password': datasource.password_encrypted,  # TODO: Implement decryption if passwords are encrypted
        'connection_string': f"{datasource.type}://{datasource.username}@{datasource.host}:{datasource.port}/{datasource.database_name}"
    }

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
        resolved_port = datasource.port

        # Create Docker container if connection_type is "docker"
        if datasource.connection_type == "docker":
            # Auto-resolve port conflicts
            if resolved_port:
                resolved_port = docker_service.find_available_port(datasource.port)
                if resolved_port != datasource.port:
                    logger.info(f"Port {datasource.port} was in use, auto-assigned port {resolved_port}")

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
                port=resolved_port,
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
            port=resolved_port,  # Use the auto-resolved port
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


@app.delete("/datasources/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Datasources"])
def delete_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """Delete a datasource and optionally remove its container"""
    # Get datasource
    datasource = db.query(crud.models.Datasource).filter(
        crud.models.Datasource.id == datasource_id
    ).first()

    if not datasource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasource with id {datasource_id} not found"
        )

    # If it's a Docker container, stop and remove it
    if datasource.connection_type == "docker" and datasource.container_id and docker_service:
        try:
            # Stop container if running
            docker_service.stop_container(datasource.container_id)
            # Remove container
            docker_service.remove_container(datasource.container_id, force=True)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Warning: Failed to remove container: {e}")

    # Delete from database
    db.delete(datasource)
    db.commit()

    return None


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

    # Auto-run setup if this is the first time starting (setup_status is pending)
    if datasource.setup_status == "pending":
        logger.info(f"Auto-running database setup for datasource {datasource_id}")
        datasource.setup_status = "configuring"
        db.commit()

        # Run setup in background (non-blocking)
        import threading
        from .database import SessionLocal

        def run_setup():
            # Create new database session for this thread
            thread_db = SessionLocal()
            try:
                # Reload datasource in this thread's session
                thread_datasource = thread_db.query(crud.models.Datasource).filter(
                    crud.models.Datasource.id == datasource_id
                ).first()

                if thread_datasource:
                    success, message = DatabaseSetupService.setup_database(thread_datasource)
                    thread_datasource.setup_status = "ready" if success else "error"
                    thread_db.commit()

                    if success:
                        logger.info(f"Database setup completed for datasource {datasource_id}")
                    else:
                        logger.error(f"Database setup failed for datasource {datasource_id}: {message}")
            except Exception as e:
                logger.error(f"Error in setup thread: {e}")
                thread_db.rollback()
            finally:
                thread_db.close()

        setup_thread = threading.Thread(target=run_setup)
        setup_thread.daemon = True
        setup_thread.start()

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


@app.post("/datasources/{datasource_id}/setup", tags=["Docker"])
def setup_datasource(datasource_id: int, db: Session = Depends(get_db)):
    """Initialize database in a running container"""
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
            detail="Setup is only available for Docker datasources"
        )

    if datasource.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Container must be running before setup. Please start the container first."
        )

    if datasource.setup_status == "ready":
        return {
            "message": "Database is already configured",
            "setup_status": "ready"
        }

    # Update status to configuring
    datasource.setup_status = "configuring"
    db.commit()

    try:
        # Run database setup
        success, message = DatabaseSetupService.setup_database(datasource)

        if success:
            datasource.setup_status = "ready"
            db.commit()
            return {
                "message": message,
                "setup_status": "ready"
            }
        else:
            datasource.setup_status = "error"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database setup failed: {message}"
            )

    except Exception as e:
        datasource.setup_status = "error"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Setup error: {str(e)}"
        )


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
# TEST EXECUTION ENDPOINTS
# ============================================================================

@app.post(
    "/projects/{project_id}/tests/run",
    response_model=schemas.TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tests"]
)
async def run_tests(
    project_id: int,
    test_config: schemas.TestRunCreate,
    db: Session = Depends(get_db)
):
    """
    Execute tests for a project

    This endpoint runs the test_runner.py script and tracks all results in the database.
    The execution is asynchronous, so the endpoint returns immediately with a test_run_id.
    Use the /tests/runs/{id}/status endpoint to check progress.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Run tests asynchronously
    try:
        test_run_id = await TestExecutionService.run_tests(
            db=db,
            project_id=project_id,
            suite_filter=test_config.suite_filter,
            verbose=test_config.verbose,
            stop_on_fail=test_config.stop_on_fail,
            triggered_by=test_config.triggered_by
        )

        # Get test run
        test_run = crud.get_test_run(db, test_run_id)
        return test_run

    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tests: {str(e)}"
        )


@app.get("/projects/{project_id}/tests/runs", response_model=List[schemas.TestRunResponse], tags=["Tests"])
def list_test_runs(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all test runs for a project

    Returns a list of test runs ordered by start time (most recent first).
    Use pagination parameters to limit results.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    test_runs = crud.get_test_runs(db, project_id, skip=skip, limit=limit)
    return test_runs


@app.get("/projects/{project_id}/tests/runs/{run_id}", response_model=schemas.TestRunDetailResponse, tags=["Tests"])
def get_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed test run results

    Returns the test run with all individual test results.
    Useful for displaying detailed test reports.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Get test run
    test_run = crud.get_test_run(db, run_id)
    if not test_run or test_run.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return test_run


@app.get("/projects/{project_id}/tests/runs/{run_id}/status", response_model=schemas.TestRunStatusResponse, tags=["Tests"])
def get_test_run_status(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Get real-time status of a test run

    Use this endpoint to poll for updates while tests are running.
    Returns progress percentage, current suite, and estimated time remaining.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Get status
    status_info = TestExecutionService.get_test_run_status(db, run_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return status_info


@app.post("/projects/{project_id}/tests/runs/{run_id}/cancel", tags=["Tests"])
async def cancel_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a running test execution

    Terminates the test runner process and marks the test run as cancelled.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import test execution service
    try:
        from .test_execution_service import TestExecutionService
    except ImportError:
        from test_execution_service import TestExecutionService

    # Cancel test run
    success = await TestExecutionService.cancel_test_run(db, run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not cancel test run {run_id} (may not be running)"
        )

    return {"message": f"Test run {run_id} cancelled successfully"}


@app.delete("/projects/{project_id}/tests/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tests"])
def delete_test_run(
    project_id: int,
    run_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a test run and all its results

    Permanently removes a test run from the database.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Delete test run
    success = crud.delete_test_run(db, run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with id {run_id} not found"
        )

    return None


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
