"""
Quantum Admin - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import logging
import time
import secrets

logger = logging.getLogger(__name__)

try:
    # Try relative imports (when running as module)
    from . import crud, schemas, models
    from .database import get_db, init_db
    from .docker_service import DockerService
    from .db_setup_service import DatabaseSetupService
    from .rag_system import get_rag_system
    from .auth_service import AuthService, UserCreate, UserLogin, UserResponse, TokenResponse, get_current_user, require_role, require_permission, UserRole, User, init_default_roles, create_default_admin
    from .websocket_server import manager, websocket_handler, EventType
    from .jenkins_pipeline import parse_qpipeline, generate_jenkinsfile, qpipeline_to_jenkinsfile, PIPELINE_TEMPLATES
except ImportError:
    # Fall back to absolute imports (when running directly)
    import crud
    import schemas
    import models
    from database import get_db, init_db
    from docker_service import DockerService
    from db_setup_service import DatabaseSetupService
    from rag_system import get_rag_system
    from auth_service import AuthService, UserCreate, UserLogin, UserResponse, TokenResponse, get_current_user, require_role, require_permission, UserRole, User, init_default_roles, create_default_admin
    from websocket_server import manager, websocket_handler, EventType
    from jenkins_pipeline import parse_qpipeline, generate_jenkinsfile, qpipeline_to_jenkinsfile, PIPELINE_TEMPLATES

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
    app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="static")

@app.get("/")
def root():
    """Redirect to frontend dashboard"""
    return RedirectResponse(url="/static/index.html")


# ============================================================================
# LIFECYCLE EVENTS
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database and Docker service on application startup"""
    global docker_service

    # Initialize database
    init_db()

    # Initialize authentication tables and default data
    try:
        from database import SessionLocal
        db = SessionLocal()
        init_default_roles(db)
        admin_user = create_default_admin(db)
        if admin_user:
            print(f"[OK] Default admin user created: admin / admin123")
        db.close()
        print("[OK] Authentication system initialized")
    except Exception as e:
        print(f"[WARN] Authentication initialization warning: {e}")

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
    
    # Decrypt password for runtime use
    try:
        from .secret_manager import decrypt_value
    except ImportError:
        from secret_manager import decrypt_value

    decrypted_password = decrypt_value(datasource.password_encrypted) if datasource.password_encrypted else None

    # Return datasource configuration for runtime use
    return {
        'name': datasource.name,
        'type': datasource.type,
        'host': datasource.host,
        'port': datasource.port,
        'database_name': datasource.database_name,
        'username': datasource.username,
        'password': decrypted_password,  # ✅ Decrypted for runtime use
        'connection_string': f"{datasource.type}://{datasource.username}:{decrypted_password}@{datasource.host}:{datasource.port}/{datasource.database_name}"
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

        # Encrypt password before storing
        try:
            from .secret_manager import encrypt_value
        except ImportError:
            from secret_manager import encrypt_value

        encrypted_password = encrypt_value(datasource.password) if datasource.password else None

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
            password_encrypted=encrypted_password,  # ✅ Encrypted!
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
# CONFIGURATION MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/projects/{project_id}/environment-variables", response_model=List[schemas.EnvironmentVariableResponse], tags=["Configuration"])
def list_environment_variables(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all environment variables for a project

    Values are returned masked for security. Use the individual endpoint to get the full value if needed.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import mask_value
    except ImportError:
        from secret_manager import mask_value

    env_vars = crud.get_environment_variables(db, project_id)

    # Convert to response format with masked values
    return [
        schemas.EnvironmentVariableResponse(
            id=env_var.id,
            project_id=env_var.project_id,
            key=env_var.key,
            value_masked=mask_value(env_var.value_encrypted) if env_var.is_secret else env_var.value_encrypted[:20] + "...",
            description=env_var.description,
            is_secret=env_var.is_secret,
            created_at=env_var.created_at,
            updated_at=env_var.updated_at
        )
        for env_var in env_vars
    ]


@app.post("/projects/{project_id}/environment-variables", response_model=schemas.EnvironmentVariableResponse, status_code=status.HTTP_201_CREATED, tags=["Configuration"])
def create_environment_variable(
    project_id: int,
    env_var: schemas.EnvironmentVariableCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new environment variable

    The value is automatically encrypted before storage.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import encrypt_value, mask_value
    except ImportError:
        from secret_manager import encrypt_value, mask_value

    # Encrypt the value
    try:
        encrypted_value = encrypt_value(env_var.value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt value: {str(e)}"
        )

    # Create environment variable
    try:
        new_env_var = crud.create_environment_variable(
            db=db,
            project_id=project_id,
            key=env_var.key,
            value_encrypted=encrypted_value,
            description=env_var.description,
            is_secret=env_var.is_secret
        )

        # Create configuration history entry
        import json
        changes = {"action": "create", "key": env_var.key, "is_secret": env_var.is_secret}
        crud.create_configuration_history(
            db=db,
            project_id=project_id,
            changes_json=json.dumps(changes),
            snapshot_json="{}",
            changed_by="api"
        )

        return schemas.EnvironmentVariableResponse(
            id=new_env_var.id,
            project_id=new_env_var.project_id,
            key=new_env_var.key,
            value_masked=mask_value(new_env_var.value_encrypted),
            description=new_env_var.description,
            is_secret=new_env_var.is_secret,
            created_at=new_env_var.created_at,
            updated_at=new_env_var.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.put("/projects/{project_id}/environment-variables/{key}", response_model=schemas.EnvironmentVariableResponse, tags=["Configuration"])
def update_environment_variable(
    project_id: int,
    key: str,
    env_var_update: schemas.EnvironmentVariableUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an environment variable

    If value is provided, it will be encrypted before storage.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Import secret manager
    try:
        from .secret_manager import encrypt_value, mask_value
    except ImportError:
        from secret_manager import encrypt_value, mask_value

    # Encrypt new value if provided
    encrypted_value = None
    if env_var_update.value is not None:
        try:
            encrypted_value = encrypt_value(env_var_update.value)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to encrypt value: {str(e)}"
            )

    # Update environment variable
    updated_env_var = crud.update_environment_variable(
        db=db,
        project_id=project_id,
        key=key,
        value_encrypted=encrypted_value,
        description=env_var_update.description,
        is_secret=env_var_update.is_secret
    )

    if not updated_env_var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment variable '{key}' not found"
        )

    # Create configuration history entry
    import json
    changes = {"action": "update", "key": key}
    if env_var_update.value is not None:
        changes["value_changed"] = True
    if env_var_update.description is not None:
        changes["description"] = env_var_update.description
    crud.create_configuration_history(
        db=db,
        project_id=project_id,
        changes_json=json.dumps(changes),
        snapshot_json="{}",
        changed_by="api"
    )

    return schemas.EnvironmentVariableResponse(
        id=updated_env_var.id,
        project_id=updated_env_var.project_id,
        key=updated_env_var.key,
        value_masked=mask_value(updated_env_var.value_encrypted),
        description=updated_env_var.description,
        is_secret=updated_env_var.is_secret,
        created_at=updated_env_var.created_at,
        updated_at=updated_env_var.updated_at
    )


@app.delete("/projects/{project_id}/environment-variables/{key}", status_code=status.HTTP_204_NO_CONTENT, tags=["Configuration"])
def delete_environment_variable(
    project_id: int,
    key: str,
    db: Session = Depends(get_db)
):
    """
    Delete an environment variable
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    # Delete environment variable
    success = crud.delete_environment_variable(db, project_id, key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment variable '{key}' not found"
        )

    # Create configuration history entry
    import json
    changes = {"action": "delete", "key": key}
    crud.create_configuration_history(
        db=db,
        project_id=project_id,
        changes_json=json.dumps(changes),
        snapshot_json="{}",
        changed_by="api"
    )

    return None


@app.get("/projects/{project_id}/configuration/history", response_model=List[schemas.ConfigurationHistoryResponse], tags=["Configuration"])
def get_configuration_history(
    project_id: int,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get configuration change history for a project

    Returns the most recent configuration changes.
    """
    # Verify project exists
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )

    history = crud.get_configuration_history(db, project_id, limit=limit)
    return history


# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "quantum_settings.json")

def load_settings_from_file():
    """Load settings from JSON file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                import json
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return {}

def save_settings_to_file(settings: dict):
    """Save settings to JSON file"""
    try:
        import json
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


@app.get("/settings", tags=["Settings"])
def get_settings():
    """
    Get all Quantum Admin settings
    """
    settings = load_settings_from_file()
    return settings


@app.post("/settings", tags=["Settings"])
def save_settings(settings: dict):
    """
    Save Quantum Admin settings
    """
    success = save_settings_to_file(settings)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings"
        )

    return {"success": True, "message": "Settings saved successfully"}


@app.post("/settings/test-email", tags=["Settings"])
def test_email_connection(email_config: dict):
    """
    Test SMTP email connection
    """
    import smtplib
    from email.mime.text import MIMEText

    try:
        smtp_host = email_config.get('smtp_host')
        smtp_port = email_config.get('smtp_port', 587)
        smtp_username = email_config.get('smtp_username')
        smtp_password = email_config.get('smtp_password')
        use_tls = email_config.get('smtp_use_tls', True)
        use_ssl = email_config.get('smtp_use_ssl', False)

        if not smtp_host or not smtp_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMTP host and username are required"
            )

        # Create SMTP connection
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)

        if use_tls and not use_ssl:
            server.starttls()

        # Login
        if smtp_password:
            server.login(smtp_username, smtp_password)

        # Send test email
        msg = MIMEText("This is a test email from Quantum Admin.")
        msg['Subject'] = 'Quantum Admin - Test Email'
        msg['From'] = smtp_username
        msg['To'] = smtp_username

        server.send_message(msg)
        server.quit()

        return {"success": True, "message": "Email connection successful"}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Authentication failed. Check username and password."}
    except smtplib.SMTPException as e:
        return {"success": False, "error": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}


# ============================================================================
# AI ASSISTANT (SLM Integration)
# ============================================================================

class QuantumAI:
    """
    Quantum AI Assistant - Rule-based system with future SLM integration
    Calibrated for Quantum framework syntax and best practices
    """

    def __init__(self):
        self.knowledge_base = {
            "databinding": {
                "patterns": ["{variable}", "{object.property}", "{array[index]}"],
                "examples": [
                    "Use {user.name} to display user name",
                    "Use {items[0].title} to access array elements",
                    "Use {session.isLoggedIn} for conditionals"
                ]
            },
            "components": {
                "structure": "<?quantum version=\"1.0\"?>\n<component name=\"mycomp\">\n  <!-- content -->\n</component>",
                "elements": ["loop", "if", "query", "form", "include"]
            },
            "best_practices": [
                "Always validate user input",
                "Use parameterized queries for database operations",
                "Implement proper error handling",
                "Keep components focused and reusable"
            ]
        }

    def respond(self, message: str, context: str = "quantum") -> str:
        """Generate response based on user message"""
        message_lower = message.lower()

        # Databinding questions
        if any(word in message_lower for word in ["databinding", "binding", "variable", "{}", "expression"]):
            return self._explain_databinding()

        # Component creation
        if any(word in message_lower for word in ["create component", "new component", "component structure"]):
            return self._explain_component_structure()

        # Loop questions
        if "loop" in message_lower:
            return self._explain_loop()

        # Conditional questions
        if any(word in message_lower for word in ["if", "conditional", "condition"]):
            return self._explain_conditional()

        # Database questions
        if any(word in message_lower for word in ["database", "query", "sql"]):
            return self._explain_database()

        # Error help
        if any(word in message_lower for word in ["error", "bug", "issue", "problem"]):
            return self._help_with_errors()

        # Best practices
        if any(word in message_lower for word in ["best practice", "should i", "how to"]):
            return self._suggest_best_practices()

        # Default response
        return self._default_response()

    def _explain_databinding(self) -> str:
        return """**Databinding in Quantum**

Quantum uses curly braces `{}` for databinding. Here are the patterns:

1. **Simple variables**: `{username}`, `{email}`
2. **Object properties**: `{user.name}`, `{user.email}`
3. **Array access**: `{items[0]}`, `{users[index]}`
4. **Nested**: `{user.address.city}`

**Example:**
```xml
<p>Hello, {user.name}!</p>
<p>You have {notifications.length} new messages</p>
```

**Context variables automatically available:**
- `{session}` - Session data
- `{user}` - Logged in user
- `{isLoggedIn}` - Authentication status
- `{request}` - Request information
"""

    def _explain_component_structure(self) -> str:
        return """**Creating a Quantum Component**

Basic structure:
```xml
<?quantum version="1.0"?>
<component name="hello">
    <h1>Hello, {name}!</h1>
    <p>This is a Quantum component</p>
</component>
```

**Best practices:**
- Use descriptive component names
- Keep components focused (single responsibility)
- Pass data via context variables
- Reuse components with `<include>`
"""

    def _explain_loop(self) -> str:
        return """**Loops in Quantum**

Use `<loop>` to iterate over arrays:

```xml
<loop array="users">
    <div class="user-card">
        <h3>{item.name}</h3>
        <p>{item.email}</p>
    </div>
</loop>
```

**Available variables inside loop:**
- `{item}` - Current item
- `{index}` - Current index (0-based)
- `{isFirst}` - True for first item
- `{isLast}` - True for last item
"""

    def _explain_conditional(self) -> str:
        return """**Conditionals in Quantum**

Use `<if>` for conditional rendering:

```xml
<if condition="{isLoggedIn}">
    <p>Welcome back, {user.name}!</p>
</if>

<if condition="{user.role == 'admin'}">
    <button>Admin Panel</button>
</if>
```

**Operators:**
- `==`, `!=` - Equality
- `>`, `<`, `>=`, `<=` - Comparison
- `and`, `or` - Logical operators
"""

    def _explain_database(self) -> str:
        return """**Database Operations in Quantum**

1. **Create a datasource** in Admin UI
2. **Use query element:**

```xml
<query name="getUsers" datasource="mydb">
    SELECT * FROM users WHERE active = true
</query>

<loop array="getUsers">
    <p>{item.username}</p>
</loop>
```

**Best practices:**
- Always use parameterized queries
- Limit results with LIMIT clause
- Handle errors gracefully
- Use connection pooling
"""

    def _help_with_errors(self) -> str:
        return """**Common Quantum Errors**

1. **Databinding not working:**
   - Check variable is in context
   - Verify correct syntax: `{var}` not `{{var}}`

2. **Component not rendering:**
   - Verify XML is well-formed
   - Check component name matches file

3. **Loop not showing data:**
   - Ensure array exists in context
   - Check array is not empty

4. **Database errors:**
   - Verify datasource is running
   - Check connection settings
   - Review query syntax

Need more specific help? Share your error message!
"""

    def _suggest_best_practices(self) -> str:
        return """**Quantum Best Practices**

**Security:**
- ✅ Always validate user input
- ✅ Use parameterized queries
- ✅ Implement authentication/authorization
- ✅ Sanitize output to prevent XSS

**Performance:**
- ✅ Use query limits to avoid large result sets
- ✅ Enable caching where appropriate
- ✅ Optimize loops for large datasets

**Code Quality:**
- ✅ Keep components small and focused
- ✅ Reuse components with `<include>`
- ✅ Use meaningful variable names
- ✅ Add comments for complex logic

**Development:**
- ✅ Enable hot reload for faster iteration
- ✅ Use Admin UI for datasource management
- ✅ Monitor logs for errors
"""

    def _default_response(self) -> str:
        return """I'm here to help with Quantum! I can assist with:

- **Databinding** - Using variables and expressions
- **Components** - Creating and structuring components
- **Loops & Conditionals** - Iterating and conditional rendering
- **Database** - Queries and datasources
- **Best Practices** - Security, performance, code quality
- **Troubleshooting** - Common errors and solutions

What would you like to know about?"""

# Initialize AI assistant
quantum_ai = QuantumAI()

@app.post("/ai/chat", tags=["AI Assistant"])
def ai_chat(request: dict):
    """
    AI Assistant endpoint with RAG (Retrieval-Augmented Generation)

    Accepts:
    - message: User's question/message
    - context: Context type (default: "quantum")

    Returns AI-generated response enhanced with relevant Quantum documentation
    using RAG system for accurate, context-aware responses
    """
    message = request.get("message", "")
    context = request.get("context", "quantum")

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is required"
        )

    # Get RAG system instance
    rag = get_rag_system()

    # Generate base response
    base_response = quantum_ai.respond(message, context)

    # Enhance response with RAG context
    enhanced_response = rag.enhance_response(message, base_response)

    # Get detected intents for debugging
    intents = rag.detect_intent(message)

    return {
        "response": enhanced_response,
        "model": "quantum-slm-v1-rag",  # RAG-enhanced model
        "context": context,
        "intents": intents  # Include detected intents in response
    }


# ============================================================================
# PERFORMANCE & DEVOPS ENDPOINTS
# ============================================================================

# Cache Management
@app.get("/cache/stats", tags=["Performance"])
def get_cache_stats():
    """Get cache statistics"""
    from cache_service import get_cache
    cache = get_cache()
    return cache.get_stats()


@app.post("/cache/clear", tags=["Performance"])
def clear_cache(namespace: Optional[str] = None):
    """Clear cache (optionally by namespace)"""
    from cache_service import get_cache
    cache = get_cache()

    if namespace:
        cleared = cache.clear_namespace(namespace)
        return {"status": "success", "cleared": cleared, "namespace": namespace}
    else:
        cache.clear_all()
        return {"status": "success", "message": "All cache cleared"}


# Rate Limiting Stats
@app.get("/rate-limit/status", tags=["Performance"])
def get_rate_limit_status(request: Request):
    """Get rate limit status for current client"""
    from rate_limiter import get_rate_limiter
    limiter = get_rate_limiter()

    result = limiter.check_rate_limit(request, 1000, 3600)
    return {
        "enabled": limiter.enabled,
        "remaining": result["remaining"],
        "reset_time": result["reset_time"],
        "limit": 1000,
        "window": 3600
    }


# Celery Task Management
@app.get("/tasks/active", tags=["DevOps"])
def get_active_tasks():
    """Get currently running background tasks"""
    from celery_tasks import get_active_tasks
    return {"tasks": get_active_tasks()}


@app.get("/tasks/{task_id}", tags=["DevOps"])
def get_task_status(task_id: str):
    """Get status of a specific task"""
    from celery_tasks import get_task_status
    return get_task_status(task_id)


@app.post("/tasks/{task_id}/cancel", tags=["DevOps"])
def cancel_task(task_id: str):
    """Cancel a running task"""
    from celery_tasks import cancel_task
    success = cancel_task(task_id)
    return {"status": "cancelled" if success else "failed", "task_id": task_id}


# Backup Tasks
@app.post("/tasks/backup", tags=["DevOps"])
def queue_backup(datasource_id: int, backup_type: str = "full"):
    """Queue database backup task"""
    from celery_tasks import backup_database
    task = backup_database.delay(datasource_id, backup_type)
    return {"status": "queued", "task_id": task.id}


@app.post("/tasks/cleanup-backups", tags=["DevOps"])
def queue_cleanup_backups(days: int = 30):
    """Queue old backup cleanup task"""
    from celery_tasks import cleanup_old_backups
    task = cleanup_old_backups.delay(days)
    return {"status": "queued", "task_id": task.id}


# Deployment Tasks
@app.post("/tasks/deploy", tags=["DevOps"])
def queue_deployment(environment: str, branch: str = "main", run_migrations: bool = True):
    """Queue deployment task"""
    from celery_tasks import deploy_application
    task = deploy_application.delay(environment, branch, run_migrations)
    return {"status": "queued", "task_id": task.id, "environment": environment}


@app.post("/tasks/rollback", tags=["DevOps"])
def queue_rollback(environment: str, target_version: str):
    """Queue rollback task"""
    from celery_tasks import rollback_deployment
    task = rollback_deployment.delay(environment, target_version)
    return {"status": "queued", "task_id": task.id}


# Git Webhooks
@app.post("/webhooks/github", tags=["DevOps"])
async def github_webhook(request: Request):
    """Handle GitHub webhook events"""
    from webhook_handler import get_webhook_handler
    handler = get_webhook_handler()
    return await handler.handle_github_webhook(request)


@app.post("/webhooks/gitlab", tags=["DevOps"])
async def gitlab_webhook(request: Request):
    """Handle GitLab webhook events"""
    from webhook_handler import get_webhook_handler
    handler = get_webhook_handler()
    return await handler.handle_gitlab_webhook(request)


# Environment Management
@app.get("/environments", tags=["DevOps"])
def list_environments():
    """List all environments"""
    from env_manager import get_env_manager
    manager = get_env_manager()
    return {"environments": manager.list_environments()}


@app.get("/environments/{name}", tags=["DevOps"])
def get_environment(name: str):
    """Get environment configuration"""
    from env_manager import get_env_manager
    manager = get_env_manager()
    config = manager.get_environment(name)

    if not config:
        raise HTTPException(status_code=404, detail="Environment not found")

    return {"environment": config}


@app.get("/environments/{name}/validate", tags=["DevOps"])
def validate_environment(name: str):
    """Validate environment configuration"""
    from env_manager import get_env_manager
    manager = get_env_manager()
    return manager.validate_environment(name)


@app.get("/environments/{name}/export", tags=["DevOps"])
def export_environment(name: str):
    """Export environment as .env file"""
    from env_manager import get_env_manager
    manager = get_env_manager()
    env_file = manager.export_env_file(name)

    if not env_file:
        raise HTTPException(status_code=404, detail="Environment not found")

    return {"env_file": env_file}


@app.post("/environments/{name}/activate", tags=["DevOps"])
def activate_environment(name: str):
    """Switch to specified environment"""
    from env_manager import get_env_manager
    manager = get_env_manager()
    success = manager.set_current_environment(name)

    if not success:
        raise HTTPException(status_code=404, detail="Environment not found")

    return {"status": "activated", "environment": name}


# Query Optimization
@app.post("/query/explain", tags=["Performance"])
def explain_query(request: dict, db: Session = Depends(get_db)):
    """Get query execution plan"""
    from query_optimizer import QueryOptimizer
    optimizer = QueryOptimizer(db)

    query = request.get("query", "")
    params = request.get("params", {})

    return optimizer.explain_query(query, params)


@app.post("/query/optimize", tags=["Performance"])
def optimize_query(request: dict):
    """Optimize SQL query"""
    from query_optimizer import QueryOptimizer

    query = request.get("query", "")
    # Create dummy optimizer for analysis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    db = Session()

    optimizer = QueryOptimizer(db)
    return optimizer.optimize_query(query)


@app.get("/query/slow", tags=["Performance"])
def get_slow_queries():
    """Get list of slow queries"""
    from query_optimizer import get_performance_monitor
    monitor = get_performance_monitor()
    return {"slow_queries": monitor.get_slow_queries()}


@app.get("/query/stats", tags=["Performance"])
def get_query_stats():
    """Get query performance statistics"""
    from query_optimizer import get_performance_monitor
    monitor = get_performance_monitor()
    return {"stats": monitor.get_query_stats()}


# System Health
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/status", tags=["System"])
def system_status():
    """Detailed system status"""
    import psutil

    return {
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "uptime_seconds": time.time() - psutil.boot_time()
    }


# ============================================================================
# CONTAINER WIZARD ENDPOINTS
# ============================================================================

@app.get("/wizard/templates", tags=["Container Wizard"])
def get_wizard_templates():
    """Get available container templates for wizard"""
    # Return simplified template list
    return {
        "templates": [
            {"id": "postgres", "name": "PostgreSQL", "category": "database"},
            {"id": "mysql", "name": "MySQL", "category": "database"},
            {"id": "mongodb", "name": "MongoDB", "category": "database"},
            {"id": "redis", "name": "Redis", "category": "cache"},
            {"id": "nginx", "name": "Nginx", "category": "web"},
            {"id": "custom", "name": "Custom", "category": "custom"}
        ]
    }


@app.post("/wizard/validate", tags=["Container Wizard"])
def validate_wizard_config(config: dict):
    """Validate container configuration"""
    errors = []
    warnings = []

    # Validate container name
    name = config.get("name", "")
    if not name:
        errors.append("Container name is required")
    elif not all(c.isalnum() or c in ['-', '_'] for c in name):
        errors.append("Container name must be alphanumeric with hyphens/underscores")

    # Validate image
    if not config.get("image"):
        errors.append("Docker image is required")

    # Check port conflicts
    ports = config.get("ports", [])
    host_ports = [p.get("host") for p in ports]
    if len(host_ports) != len(set(host_ports)):
        errors.append("Duplicate host ports detected")

    # Resource warnings
    memory = config.get("memory", 0)
    if memory > 8:
        warnings.append("Memory limit over 8GB may impact host")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@app.post("/wizard/generate-yaml", tags=["Container Wizard"])
def generate_docker_compose(config: dict):
    """Generate docker-compose.yml from config"""
    # This would generate the actual YAML
    # For now, return a simple response
    return {
        "yaml": "version: '3.8'\nservices:\n  " + config.get("name", "service") + ":\n    image: " + config.get("image", ""),
        "filename": "docker-compose.yml"
    }


@app.post("/wizard/deploy", tags=["Container Wizard"])
async def deploy_wizard_containers(config: dict):
    """Deploy containers from wizard configuration"""
    try:
        # In production: actually deploy using Docker API
        from celery_tasks import deploy_application

        # Queue deployment task
        task = deploy_application.delay(
            environment="local",
            branch="main",
            run_migrations=False
        )

        return {
            "status": "queued",
            "task_id": task.id,
            "message": "Deployment queued successfully"
        }

    except Exception as e:
        logger.error(f"Wizard deployment failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
def register_user(
    user_create: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    auth_service = AuthService(db)
    try:
        user = auth_service.create_user(user_create)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
    except HTTPException as e:
        raise e


@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(
    user_login: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login and get JWT tokens"""
    auth_service = AuthService(db)

    # Authenticate user
    user = auth_service.authenticate_user(user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Generate tokens
    token_jti = secrets.token_urlsafe(32)
    refresh_token_jti = secrets.token_urlsafe(32)

    access_token = auth_service.create_access_token(user, jti=token_jti)
    refresh_token = auth_service.create_refresh_token(user, jti=refresh_token_jti)

    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    auth_service.create_session(
        user=user,
        token_jti=token_jti,
        refresh_token_jti=refresh_token_jti,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Return tokens and user info
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        last_login=user.last_login
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,  # 30 minutes in seconds
        user=user_response
    )


@app.post("/auth/logout", tags=["Authentication"])
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke current session"""
    auth_service = AuthService(db)

    # Get token from request (we'd need to extract JTI from the token in production)
    # For now, we'll just return success
    return {"message": "Logged out successfully"}


@app.get("/auth/verify", tags=["Authentication"])
def verify_token(
    current_user: User = Depends(get_current_user)
):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username
    }


@app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@app.get("/auth/users", tags=["Authentication"])
def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all users (Admin only)"""
    users = db.query(User).all()
    return {
        "users": [
            UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                roles=[role.name for role in user.roles],
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ]
    }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket_handler(websocket, client_id)


@app.get("/ws/stats", tags=["WebSocket"])
def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return manager.get_stats()


# ============================================================================
# JENKINS PIPELINE ENDPOINTS
# ============================================================================

@app.get("/pipeline/templates", tags=["Pipeline"])
def get_pipeline_templates():
    """Get available pipeline templates"""
    return {
        "templates": [
            {
                "id": "basic-build",
                "name": "Basic Build Pipeline",
                "description": "Simple build and test pipeline",
                "icon": "🏗️"
            },
            {
                "id": "docker-deploy",
                "name": "Docker Deploy Pipeline",
                "description": "Build and deploy Docker images",
                "icon": "🐳"
            },
            {
                "id": "parallel-tests",
                "name": "Parallel Test Pipeline",
                "description": "Run tests in parallel stages",
                "icon": "⚡"
            }
        ]
    }


@app.get("/pipeline/template/{template_id}", tags=["Pipeline"])
def get_pipeline_template(template_id: str):
    """Get a specific pipeline template"""
    if template_id not in PIPELINE_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_id": template_id,
        "xml_content": PIPELINE_TEMPLATES[template_id]
    }


@app.post("/pipeline/validate", tags=["Pipeline"])
def validate_pipeline(data: dict):
    """Validate <q:pipeline> XML syntax"""
    xml_content = data.get("xml_content", "")

    try:
        pipeline = parse_qpipeline(xml_content)
        return {
            "valid": True,
            "pipeline_name": pipeline.name,
            "stages_count": len(pipeline.stages),
            "message": "Pipeline XML is valid"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
            "message": "Invalid pipeline XML"
        }


@app.post("/pipeline/generate", tags=["Pipeline"])
def generate_pipeline_jenkinsfile(data: dict):
    """Generate Jenkinsfile from <q:pipeline> XML"""
    xml_content = data.get("xml_content", "")

    try:
        jenkinsfile = qpipeline_to_jenkinsfile(xml_content)
        pipeline = parse_qpipeline(xml_content)

        return {
            "status": "success",
            "jenkinsfile": jenkinsfile,
            "pipeline_name": pipeline.name,
            "stages_count": len(pipeline.stages)
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate Jenkinsfile: {str(e)}"
        )


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
