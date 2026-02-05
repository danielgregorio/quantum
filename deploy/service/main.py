"""
Quantum Deploy Service - Main Entry Point

FastAPI service for deploying and managing Quantum applications.
Handles uploads, container management, and nginx configuration.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import deploy, apps, health
from services.registry_service import RegistryService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Quantum Deploy Service starting...")

    # Initialize database
    registry = RegistryService()
    registry.init_db()
    logger.info("Registry database initialized")

    # Ensure directories exist
    data_dirs = [
        os.environ.get('QUANTUM_APPS_DIR', '/data/quantum/apps'),
        os.environ.get('QUANTUM_NGINX_DIR', '/data/quantum/nginx'),
        os.environ.get('QUANTUM_REGISTRY_DIR', '/data/quantum/registry'),
    ]
    for dir_path in data_dirs:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")

    yield

    # Shutdown
    logger.info("Quantum Deploy Service shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Quantum Deploy Service",
    description="Deploy and manage Quantum applications",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Key validation middleware
@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    """Validate API key for protected endpoints."""
    # Skip validation for health check
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
        return await call_next(request)

    # Get API key from environment
    expected_key = os.environ.get('QUANTUM_API_KEY')

    # If no key configured, allow all (development mode)
    if not expected_key:
        logger.warning("QUANTUM_API_KEY not set - running in development mode")
        return await call_next(request)

    # Validate API key
    api_key = request.headers.get('X-API-Key')
    if api_key != expected_key:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing API key"}
        )

    return await call_next(request)


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(deploy.router, prefix="/api", tags=["Deploy"])
app.include_router(apps.router, prefix="/api", tags=["Apps"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Quantum Deploy Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.environ.get('DEPLOY_HOST', '0.0.0.0'),
        port=int(os.environ.get('DEPLOY_PORT', 9000)),
        reload=os.environ.get('DEPLOY_DEBUG', 'false').lower() == 'true'
    )
