"""
Global Error Handlers for Quantum Admin
Provides comprehensive error handling for all API endpoints
"""

import logging
import traceback
from typing import Union, Dict, Any
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

# Setup logging
logger = logging.getLogger(__name__)


class QuantumException(Exception):
    """Base exception for Quantum Admin"""
    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(QuantumException):
    """Database operation errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=500, details=details)


class AuthenticationError(QuantumException):
    """Authentication failures"""
    def __init__(self, message: str = "Authentication failed", details: Dict[str, Any] = None):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(QuantumException):
    """Authorization/permission errors"""
    def __init__(self, message: str = "Permission denied", details: Dict[str, Any] = None):
        super().__init__(message, status_code=403, details=details)


class ResourceNotFoundError(QuantumException):
    """Resource not found errors"""
    def __init__(self, resource: str, identifier: Union[str, int]):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, status_code=404, details={"resource": resource, "id": identifier})


class ValidationError(QuantumException):
    """Input validation errors"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message, status_code=422, details={"errors": errors or []})


def create_error_response(
    status_code: int,
    message: str,
    details: Dict[str, Any] = None,
    request: Request = None
) -> JSONResponse:
    """
    Create standardized error response

    Args:
        status_code: HTTP status code
        message: Error message
        details: Additional error details
        request: FastAPI request object

    Returns:
        JSONResponse with error information
    """
    error_response = {
        "error": True,
        "status_code": status_code,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if details:
        error_response["details"] = details

    if request:
        error_response["path"] = str(request.url.path)
        error_response["method"] = request.method

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


# ============================================================================
# Exception Handlers
# ============================================================================

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI HTTPException
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={"path": request.url.path, "method": request.method}
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.detail,
        request=request
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error: {len(errors)} errors",
        extra={"path": request.url.path, "errors": errors}
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        details={"errors": errors},
        request=request
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors
    """
    logger.error(
        f"Database error: {str(exc)}",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True
    )

    # Check for specific error types
    if isinstance(exc, IntegrityError):
        return create_error_response(
            status_code=status.HTTP_409_CONFLICT,
            message="Database integrity constraint violated",
            details={"error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)},
            request=request
        )

    # Generic database error
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error occurred",
        details={"error": "A database error occurred. Please try again."},
        request=request
    )


async def quantum_exception_handler(request: Request, exc: QuantumException) -> JSONResponse:
    """
    Handle custom Quantum exceptions
    """
    logger.error(
        f"Quantum error: {exc.message}",
        extra={"path": request.url.path, "status_code": exc.status_code},
        exc_info=True
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details,
        request=request
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions
    """
    # Log full traceback
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )

    # In production, don't expose internal error details
    # In development, include more information
    import os
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"

    details = {}
    if debug_mode:
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc().split("\n")
        }

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        details=details if debug_mode else {"error": "An unexpected error occurred"},
        request=request
    )


# ============================================================================
# Error Handler Registration
# ============================================================================

def register_error_handlers(app):
    """
    Register all error handlers with FastAPI app

    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import RequestValidationError

    # Custom exceptions
    app.add_exception_handler(QuantumException, quantum_exception_handler)
    app.add_exception_handler(DatabaseError, quantum_exception_handler)
    app.add_exception_handler(AuthenticationError, quantum_exception_handler)
    app.add_exception_handler(AuthorizationError, quantum_exception_handler)
    app.add_exception_handler(ResourceNotFoundError, quantum_exception_handler)

    # FastAPI built-in exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Database exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, global_exception_handler)

    logger.info("Error handlers registered successfully")


# ============================================================================
# Utility Functions
# ============================================================================

def raise_not_found(resource: str, identifier: Union[str, int]):
    """
    Raise ResourceNotFoundError

    Usage:
        user = db.query(User).get(user_id)
        if not user:
            raise_not_found("User", user_id)
    """
    raise ResourceNotFoundError(resource, identifier)


def raise_validation_error(message: str, errors: list = None):
    """
    Raise ValidationError

    Usage:
        if not valid_email(email):
            raise_validation_error("Invalid email format")
    """
    raise ValidationError(message, errors)


def raise_auth_error(message: str = "Authentication failed"):
    """
    Raise AuthenticationError

    Usage:
        if not verify_token(token):
            raise_auth_error("Invalid token")
    """
    raise AuthenticationError(message)


def raise_permission_error(message: str = "Permission denied"):
    """
    Raise AuthorizationError

    Usage:
        if not user.is_admin:
            raise_permission_error("Admin access required")
    """
    raise AuthorizationError(message)
