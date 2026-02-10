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
    source_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: Optional[str] = "main"


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")
    source_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    status: str
    source_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: Optional[str] = None
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
    setup_status: str
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

    # Metadata counters
    function_count: int = 0
    endpoint_count: int = 0
    query_count: int = 0

    # Test tracking
    test_count: int = 0
    tests_passing: int = 0
    tests_failing: int = 0
    last_test_run_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    def get_has_tests(self) -> bool:
        """Check if component has tests"""
        return self.test_count > 0

    def get_test_coverage(self) -> int:
        """Calculate test coverage percentage"""
        if self.test_count == 0:
            return 0
        return int((self.tests_passing / self.test_count) * 100)


# ============================================================================
# COMPONENT TEST SCHEMAS
# ============================================================================

class ComponentTestCreate(BaseModel):
    """Schema for creating a component test record"""
    component_id: int
    test_file: str = Field(..., min_length=1, max_length=512)
    test_name: str = Field(..., min_length=1, max_length=255)
    test_type: str = Field(default="unit", pattern="^(unit|integration|api|e2e)$")
    generated_by: Optional[str] = Field(default="auto", pattern="^(auto|manual)$")


class ComponentTestUpdate(BaseModel):
    """Schema for updating a component test record"""
    last_status: Optional[str] = Field(None, pattern="^(passed|failed|skipped|pending|error)$")
    last_run_at: Optional[datetime] = None
    last_duration_seconds: Optional[int] = None
    last_error_message: Optional[str] = None


class ComponentTestResponse(BaseModel):
    """Schema for component test response"""
    id: int
    component_id: int
    test_file: str
    test_name: str
    test_type: str
    generated_at: Optional[datetime]
    generated_by: Optional[str]
    last_status: Optional[str]
    last_run_at: Optional[datetime]
    last_duration_seconds: Optional[int]
    last_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateTestsRequest(BaseModel):
    """Schema for test generation request"""
    test_types: List[str] = Field(default=["unit", "api"], description="Types of tests to generate")
    output_dir: Optional[str] = Field(default="tests/", description="Output directory for test files")


class GenerateTestsResponse(BaseModel):
    """Schema for test generation response"""
    component_id: int
    component_name: str
    generated: int
    tests: List[dict]


class RunComponentTestsRequest(BaseModel):
    """Schema for running component tests"""
    test_types: Optional[List[str]] = Field(default=None, description="Optional filter by test types")
    verbose: bool = Field(default=False, description="Verbose output")


class RunComponentTestsResponse(BaseModel):
    """Schema for component tests run response"""
    test_run_id: int
    component_id: int
    status: str
    message: str


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


# ============================================================================
# TEST EXECUTION SCHEMAS
# ============================================================================

class TestRunCreate(BaseModel):
    """Schema for creating a new test run"""
    suite_filter: Optional[str] = Field(None, description="Optional suite name to run (e.g., 'phase1', 'phase2')")
    verbose: bool = Field(False, description="Enable verbose output")
    stop_on_fail: bool = Field(False, description="Stop execution on first failure")
    triggered_by: str = Field("manual", description="Who/what triggered the test (manual, ci/cd, schedule)")


class TestResultResponse(BaseModel):
    """Schema for test result response"""
    id: int
    test_run_id: int
    suite_name: str
    test_file: str
    status: str
    duration_seconds: Optional[int]
    error_message: Optional[str]
    output: Optional[str]

    class Config:
        from_attributes = True


class TestRunResponse(BaseModel):
    """Schema for test run response"""
    id: int
    project_id: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration_seconds: Optional[int]
    triggered_by: Optional[str]
    suite_filter: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TestRunDetailResponse(TestRunResponse):
    """Test run with all test results"""
    test_results: List[TestResultResponse] = []

    class Config:
        from_attributes = True


class TestRunStatusResponse(BaseModel):
    """Schema for real-time test run status"""
    id: int
    status: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    current_suite: Optional[str]
    progress_percentage: Optional[float]
    estimated_time_remaining: Optional[int]

    class Config:
        from_attributes = True


# ============================================================================
# CONFIGURATION MANAGEMENT SCHEMAS
# ============================================================================

class EnvironmentVariableCreate(BaseModel):
    """Schema for creating an environment variable"""
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., description="Plain text value (will be encrypted)")
    description: Optional[str] = None
    is_secret: bool = Field(False, description="If true, value is masked in responses")


class EnvironmentVariableUpdate(BaseModel):
    """Schema for updating an environment variable"""
    value: Optional[str] = Field(None, description="New plain text value (will be encrypted)")
    description: Optional[str] = None
    is_secret: Optional[bool] = None


class EnvironmentVariableResponse(BaseModel):
    """Schema for environment variable response"""
    id: int
    project_id: int
    key: str
    value_masked: str = Field(..., description="Masked value for display (e.g., ****xyz)")
    description: Optional[str]
    is_secret: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigurationHistoryResponse(BaseModel):
    """Schema for configuration history response"""
    id: int
    project_id: int
    version: int
    changed_at: datetime
    changed_by: Optional[str]
    changes_json: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# DEPLOYMENT AUTOMATION SCHEMAS
# ============================================================================

class DeploymentTargetCreate(BaseModel):
    """Schema for creating a deployment target"""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(local|docker|ssh|kubernetes)$")
    config_json: Optional[str] = Field(None, description="JSON configuration for target")
    is_active: bool = True


class DeploymentTargetResponse(BaseModel):
    """Schema for deployment target response"""
    id: int
    project_id: int
    name: str
    type: str
    config_json: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentCreate(BaseModel):
    """Schema for creating a deployment"""
    target_id: int
    version: Optional[str] = Field(None, description="Git commit, tag, or version")
    triggered_by: str = Field("manual", description="Who/what triggered deployment")


class DeploymentResponse(BaseModel):
    """Schema for deployment response"""
    id: int
    project_id: int
    target_id: int
    version: Optional[str]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    triggered_by: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DeploymentDetailResponse(DeploymentResponse):
    """Schema for deployment response with logs"""
    build_log: Optional[str]
    deploy_log: Optional[str]
    rollback_from: Optional[int]

    class Config:
        from_attributes = True
