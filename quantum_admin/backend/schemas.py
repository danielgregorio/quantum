"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# PROJECT SCHEMAS
# ============================================================================

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class ProjectResponse(ProjectBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enables ORM mode


# ============================================================================
# DATASOURCE SCHEMAS
# ============================================================================

class DatasourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(postgres|mysql|mongodb)$")
    connection_type: str = Field(..., pattern="^(docker|direct)$")


class DatasourceCreate(DatasourceBase):
    # Docker fields
    image: Optional[str] = None
    port: Optional[int] = None

    # Direct connection fields
    host: Optional[str] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Will be encrypted before storage

    auto_start: bool = False


class DatasourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern="^(running|stopped|error)$")
    health_status: Optional[str] = Field(None, pattern="^(healthy|unhealthy|unknown)$")
    auto_start: Optional[bool] = None


class DatasourceResponse(DatasourceBase):
    id: int
    project_id: int
    container_id: Optional[str]
    image: Optional[str]
    port: Optional[int]
    host: Optional[str]
    database_name: Optional[str]
    username: Optional[str]
    status: str
    health_status: str
    auto_start: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# COMPONENT SCHEMAS
# ============================================================================

class ComponentResponse(BaseModel):
    id: int
    project_id: int
    name: str
    file_path: str
    status: str
    error_message: Optional[str]
    last_compiled: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# ENDPOINT SCHEMAS
# ============================================================================

class EndpointResponse(BaseModel):
    id: int
    project_id: int
    component_id: Optional[int]
    method: str
    path: str
    function_name: str
    description: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# DETAILED RESPONSES (with nested data)
# ============================================================================

class ProjectDetailResponse(ProjectResponse):
    """Project with all related data"""
    datasources: List[DatasourceResponse] = []
    components: List[ComponentResponse] = []
    endpoints: List[EndpointResponse] = []

    class Config:
        from_attributes = True
