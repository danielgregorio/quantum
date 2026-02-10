"""
Component Discovery Service - Automatically discover and parse Quantum components

Features:
- Scan project directories for .q files
- Parse .q files to extract metadata
- Extract endpoints, functions, queries
- Validate component syntax
- Track component dependencies
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET
from sqlalchemy.orm import Session

try:
    from .models import Project, Component, Endpoint, ComponentTest
except ImportError:
    from models import Project, Component, Endpoint, ComponentTest

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredFunction:
    """Represents a function discovered in a component"""
    name: str
    params: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    description: Optional[str] = None
    line_number: int = 0


@dataclass
class DiscoveredEndpoint:
    """Represents an endpoint discovered in a component"""
    method: str  # GET, POST, PUT, DELETE
    path: str
    function_name: str
    description: Optional[str] = None
    line_number: int = 0


@dataclass
class DiscoveredQuery:
    """Represents a database query discovered in a component"""
    name: str
    datasource: Optional[str] = None
    query_type: str = "select"  # select, insert, update, delete, exec
    line_number: int = 0


@dataclass
class DiscoveredDependency:
    """Represents a component dependency"""
    component_name: str
    import_path: Optional[str] = None
    line_number: int = 0


@dataclass
class ComponentMetadata:
    """Complete metadata for a discovered component"""
    name: str
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None

    # Discovered elements
    functions: List[DiscoveredFunction] = field(default_factory=list)
    endpoints: List[DiscoveredEndpoint] = field(default_factory=list)
    queries: List[DiscoveredQuery] = field(default_factory=list)
    dependencies: List[DiscoveredDependency] = field(default_factory=list)

    # Variables and state
    variables: List[str] = field(default_factory=list)

    # Validation
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Stats
    line_count: int = 0
    last_modified: Optional[datetime] = None


class QuantumParser:
    """Parser for Quantum .q files"""

    # Quantum namespace
    Q_NAMESPACE = "q"

    # Tag patterns for extraction
    COMPONENT_PATTERN = re.compile(r'<q:component\s+name=["\']([^"\']+)["\']', re.IGNORECASE)
    FUNCTION_PATTERN = re.compile(r'<q:function\s+name=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
    ENDPOINT_PATTERN = re.compile(r'<q:endpoint\s+([^>]+)>', re.IGNORECASE)
    QUERY_PATTERN = re.compile(r'<q:query\s+name=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
    SET_PATTERN = re.compile(r'<q:set\s+var=["\']([^"\']+)["\']', re.IGNORECASE)
    IMPORT_PATTERN = re.compile(r'<q:import\s+component=["\']([^"\']+)["\']', re.IGNORECASE)
    INCLUDE_PATTERN = re.compile(r'<q:include\s+file=["\']([^"\']+)["\']', re.IGNORECASE)

    # HTTP method patterns
    HTTP_GET_PATTERN = re.compile(r'<q:http-get\s+path=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
    HTTP_POST_PATTERN = re.compile(r'<q:http-post\s+path=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
    HTTP_PUT_PATTERN = re.compile(r'<q:http-put\s+path=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)
    HTTP_DELETE_PATTERN = re.compile(r'<q:http-delete\s+path=["\']([^"\']+)["\']([^>]*)>', re.IGNORECASE)

    @classmethod
    def parse_file(cls, file_path: str) -> ComponentMetadata:
        """Parse a .q file and extract metadata"""
        path = Path(file_path)

        if not path.exists():
            return ComponentMetadata(
                name=path.stem,
                file_path=str(path),
                is_valid=False,
                errors=["File not found"]
            )

        try:
            content = path.read_text(encoding='utf-8')
            lines = content.split('\n')
            line_count = len(lines)
            last_modified = datetime.fromtimestamp(path.stat().st_mtime)

            # Extract component name
            name_match = cls.COMPONENT_PATTERN.search(content)
            component_name = name_match.group(1) if name_match else path.stem

            metadata = ComponentMetadata(
                name=component_name,
                file_path=str(path),
                line_count=line_count,
                last_modified=last_modified
            )

            # Parse functions
            metadata.functions = cls._parse_functions(content)

            # Parse endpoints (both explicit and HTTP method tags)
            metadata.endpoints = cls._parse_endpoints(content)

            # Parse queries
            metadata.queries = cls._parse_queries(content)

            # Parse dependencies
            metadata.dependencies = cls._parse_dependencies(content)

            # Parse variables
            metadata.variables = cls._parse_variables(content)

            # Validate XML structure
            validation_errors = cls._validate_xml(content)
            if validation_errors:
                metadata.warnings.extend(validation_errors)

            return metadata

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return ComponentMetadata(
                name=path.stem,
                file_path=str(path),
                is_valid=False,
                errors=[str(e)]
            )

    @classmethod
    def _parse_functions(cls, content: str) -> List[DiscoveredFunction]:
        """Extract function definitions from content"""
        functions = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            match = cls.FUNCTION_PATTERN.search(line)
            if match:
                name = match.group(1)
                attrs = match.group(2)

                # Extract parameters
                params = []
                params_match = re.search(r'params=["\']([^"\']+)["\']', attrs)
                if params_match:
                    params = [p.strip() for p in params_match.group(1).split(',')]

                # Extract return type
                return_type = None
                return_match = re.search(r'returns=["\']([^"\']+)["\']', attrs)
                if return_match:
                    return_type = return_match.group(1)

                functions.append(DiscoveredFunction(
                    name=name,
                    params=params,
                    return_type=return_type,
                    line_number=i + 1
                ))

        return functions

    @classmethod
    def _parse_endpoints(cls, content: str) -> List[DiscoveredEndpoint]:
        """Extract endpoint definitions from content"""
        endpoints = []
        lines = content.split('\n')

        # Parse explicit q:endpoint tags
        for i, line in enumerate(lines):
            match = cls.ENDPOINT_PATTERN.search(line)
            if match:
                attrs = match.group(1)

                method_match = re.search(r'method=["\']([^"\']+)["\']', attrs)
                path_match = re.search(r'path=["\']([^"\']+)["\']', attrs)
                func_match = re.search(r'function=["\']([^"\']+)["\']', attrs)

                if path_match:
                    endpoints.append(DiscoveredEndpoint(
                        method=method_match.group(1).upper() if method_match else "GET",
                        path=path_match.group(1),
                        function_name=func_match.group(1) if func_match else "",
                        line_number=i + 1
                    ))

        # Parse HTTP method tags (q:http-get, q:http-post, etc.)
        http_patterns = [
            (cls.HTTP_GET_PATTERN, "GET"),
            (cls.HTTP_POST_PATTERN, "POST"),
            (cls.HTTP_PUT_PATTERN, "PUT"),
            (cls.HTTP_DELETE_PATTERN, "DELETE"),
        ]

        for i, line in enumerate(lines):
            for pattern, method in http_patterns:
                match = pattern.search(line)
                if match:
                    path = match.group(1)
                    attrs = match.group(2)

                    func_match = re.search(r'function=["\']([^"\']+)["\']', attrs)

                    endpoints.append(DiscoveredEndpoint(
                        method=method,
                        path=path,
                        function_name=func_match.group(1) if func_match else "",
                        line_number=i + 1
                    ))

        return endpoints

    @classmethod
    def _parse_queries(cls, content: str) -> List[DiscoveredQuery]:
        """Extract query definitions from content"""
        queries = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            match = cls.QUERY_PATTERN.search(line)
            if match:
                name = match.group(1)
                attrs = match.group(2)

                datasource = None
                ds_match = re.search(r'datasource=["\']([^"\']+)["\']', attrs)
                if ds_match:
                    datasource = ds_match.group(1)

                # Determine query type from content
                query_type = "select"
                if re.search(r'type=["\'](\w+)["\']', attrs):
                    type_match = re.search(r'type=["\'](\w+)["\']', attrs)
                    query_type = type_match.group(1).lower()

                queries.append(DiscoveredQuery(
                    name=name,
                    datasource=datasource,
                    query_type=query_type,
                    line_number=i + 1
                ))

        return queries

    @classmethod
    def _parse_dependencies(cls, content: str) -> List[DiscoveredDependency]:
        """Extract component dependencies from content"""
        dependencies = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check q:import
            import_match = cls.IMPORT_PATTERN.search(line)
            if import_match:
                dependencies.append(DiscoveredDependency(
                    component_name=import_match.group(1),
                    line_number=i + 1
                ))

            # Check q:include
            include_match = cls.INCLUDE_PATTERN.search(line)
            if include_match:
                dependencies.append(DiscoveredDependency(
                    component_name=include_match.group(1),
                    import_path=include_match.group(1),
                    line_number=i + 1
                ))

        return dependencies

    @classmethod
    def _parse_variables(cls, content: str) -> List[str]:
        """Extract variable names from content"""
        variables = set()

        for match in cls.SET_PATTERN.finditer(content):
            variables.add(match.group(1))

        return list(variables)

    @classmethod
    def _validate_xml(cls, content: str) -> List[str]:
        """Validate XML structure and return any errors"""
        errors = []

        # Wrap content in root element for parsing
        wrapped = f"<root xmlns:q='quantum'>{content}</root>"

        try:
            ET.fromstring(wrapped)
        except ET.ParseError as e:
            errors.append(f"XML parse error: {e}")

        return errors


class ComponentDiscoveryService:
    """Service for discovering components in a project"""

    def __init__(self, db: Session):
        self.db = db
        self.parser = QuantumParser()

    def discover_components(
        self,
        project_id: int,
        base_path: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[ComponentMetadata]:
        """
        Discover all components in a project

        Args:
            project_id: Project ID
            base_path: Base path to scan (defaults to project path)
            include_patterns: Glob patterns to include
            exclude_patterns: Glob patterns to exclude

        Returns:
            List of discovered component metadata
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Determine base path - try project settings or use current directory
        if not base_path:
            # Project model may not have path field - use current directory as fallback
            base_path = getattr(project, 'path', None) or getattr(project, 'root_path', None) or "."

        if not os.path.isabs(base_path):
            base_path = os.path.abspath(base_path)

        if not os.path.exists(base_path):
            logger.warning(f"Project path does not exist: {base_path}")
            return []

        # Default patterns
        if include_patterns is None:
            include_patterns = ["**/*.q", "**/*.quantum"]

        if exclude_patterns is None:
            exclude_patterns = ["**/node_modules/**", "**/.git/**", "**/venv/**", "**/__pycache__/**"]

        # Find all .q files
        discovered = []
        base = Path(base_path)

        for pattern in include_patterns:
            for file_path in base.glob(pattern):
                # Check exclusions
                rel_path = str(file_path.relative_to(base))
                excluded = False

                for exclude in exclude_patterns:
                    if file_path.match(exclude):
                        excluded = True
                        break

                if not excluded:
                    metadata = self.parser.parse_file(str(file_path))
                    discovered.append(metadata)

        return discovered

    def sync_components(
        self,
        project_id: int,
        base_path: Optional[str] = None
    ) -> Tuple[int, int, int]:
        """
        Sync discovered components with database

        Returns:
            Tuple of (created, updated, deleted) counts
        """
        # Discover components
        discovered = self.discover_components(project_id, base_path)
        discovered_paths = {m.file_path for m in discovered}

        # Get existing components
        existing = self.db.query(Component).filter(
            Component.project_id == project_id
        ).all()
        existing_map = {c.file_path: c for c in existing}

        created = 0
        updated = 0
        deleted = 0

        # Process discovered components
        for metadata in discovered:
            if metadata.file_path in existing_map:
                # Update existing
                component = existing_map[metadata.file_path]
                component.name = metadata.name
                component.status = "active" if metadata.is_valid else "error"
                component.error_message = "; ".join(metadata.errors) if metadata.errors else None
                component.last_compiled = metadata.last_modified

                # Update counters
                component.function_count = len(metadata.functions)
                component.endpoint_count = len(metadata.endpoints)
                component.query_count = len(metadata.queries)

                updated += 1

                # Sync endpoints
                self._sync_endpoints(component.id, project_id, metadata.endpoints)
            else:
                # Create new
                component = Component(
                    project_id=project_id,
                    name=metadata.name,
                    file_path=metadata.file_path,
                    status="active" if metadata.is_valid else "error",
                    error_message="; ".join(metadata.errors) if metadata.errors else None,
                    last_compiled=metadata.last_modified,
                    function_count=len(metadata.functions),
                    endpoint_count=len(metadata.endpoints),
                    query_count=len(metadata.queries)
                )
                self.db.add(component)
                self.db.flush()  # Get component ID
                created += 1

                # Create endpoints
                self._sync_endpoints(component.id, project_id, metadata.endpoints)

        # Remove deleted components
        for file_path, component in existing_map.items():
            if file_path not in discovered_paths:
                # Delete endpoints first
                self.db.query(Endpoint).filter(
                    Endpoint.component_id == component.id
                ).delete()
                self.db.delete(component)
                deleted += 1

        self.db.commit()

        return created, updated, deleted

    def _sync_endpoints(
        self,
        component_id: int,
        project_id: int,
        endpoints: List[DiscoveredEndpoint]
    ):
        """Sync endpoints for a component"""
        # Delete existing endpoints for this component
        self.db.query(Endpoint).filter(
            Endpoint.component_id == component_id
        ).delete()

        # Create new endpoints
        for ep in endpoints:
            endpoint = Endpoint(
                project_id=project_id,
                component_id=component_id,
                method=ep.method,
                path=ep.path,
                function_name=ep.function_name,
                description=ep.description
            )
            self.db.add(endpoint)

    def get_component_details(
        self,
        project_id: int,
        component_id: int
    ) -> Optional[ComponentMetadata]:
        """Get detailed metadata for a specific component"""
        component = self.db.query(Component).filter(
            Component.id == component_id,
            Component.project_id == project_id
        ).first()

        if not component:
            return None

        return self.parser.parse_file(component.file_path)

    def validate_component(
        self,
        file_path: str
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a component file

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        metadata = self.parser.parse_file(file_path)
        return metadata.is_valid, metadata.errors, metadata.warnings

    def get_dependency_graph(
        self,
        project_id: int,
        base_path: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Build dependency graph for all components

        Args:
            project_id: Project ID
            base_path: Optional base path to scan

        Returns:
            Dict mapping component names to their dependencies
        """
        discovered = self.discover_components(project_id, base_path)

        graph = {}
        for metadata in discovered:
            deps = [d.component_name for d in metadata.dependencies]
            graph[metadata.name] = deps

        return graph

    def find_unused_components(
        self,
        project_id: int,
        base_path: Optional[str] = None
    ) -> List[str]:
        """Find components that are not imported by any other component"""
        graph = self.get_dependency_graph(project_id, base_path)

        # Get all component names
        all_components = set(graph.keys())

        # Get all referenced components
        referenced = set()
        for deps in graph.values():
            referenced.update(deps)

        # Find unused (not referenced by any other)
        unused = all_components - referenced

        return list(unused)

    def discover_existing_tests(
        self,
        project_id: int,
        tests_dir: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover existing test files and match them to components

        Args:
            project_id: Project ID
            tests_dir: Directory containing tests (defaults to project/tests)

        Returns:
            Dict mapping component names to list of discovered test info
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {}

        # Determine tests directory
        if not tests_dir:
            base = project.source_path or "."
            tests_dir = os.path.join(base, "tests")

        if not os.path.exists(tests_dir):
            return {}

        discovered_tests: Dict[str, List[Dict[str, Any]]] = {}

        # Scan for test files
        test_path = Path(tests_dir)
        for test_file in test_path.glob("**/test_*.py"):
            # Parse test file to extract test functions
            try:
                content = test_file.read_text(encoding='utf-8')
                file_path = str(test_file)

                # Extract component name from file (test_<component>.py)
                file_stem = test_file.stem  # test_user_login
                component_name = file_stem.replace("test_", "").replace("_", "")

                # Find test functions
                test_pattern = re.compile(r'def (test_\w+)\s*\(')
                for match in test_pattern.finditer(content):
                    test_name = match.group(1)

                    # Determine test type from path or name
                    test_type = "unit"
                    if "integration" in str(test_file).lower():
                        test_type = "integration"
                    elif "api" in str(test_file).lower() or "endpoint" in test_name.lower():
                        test_type = "api"
                    elif "e2e" in str(test_file).lower():
                        test_type = "e2e"

                    if component_name not in discovered_tests:
                        discovered_tests[component_name] = []

                    discovered_tests[component_name].append({
                        "test_file": file_path,
                        "test_name": test_name,
                        "test_type": test_type
                    })

            except Exception as e:
                logger.warning(f"Error parsing test file {test_file}: {e}")

        return discovered_tests

    def sync_component_tests(
        self,
        project_id: int,
        tests_dir: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        Sync discovered tests with database

        Returns:
            Tuple of (tests_synced, components_updated)
        """
        from datetime import datetime

        discovered = self.discover_existing_tests(project_id, tests_dir)
        tests_synced = 0
        components_updated = 0

        # Get all components for this project
        components = self.db.query(Component).filter(
            Component.project_id == project_id
        ).all()

        component_map = {c.name.lower(): c for c in components}

        for comp_name_key, tests in discovered.items():
            # Try to find matching component
            component = component_map.get(comp_name_key.lower())
            if not component:
                # Try with underscores removed
                for name, comp in component_map.items():
                    if name.replace("_", "") == comp_name_key.lower():
                        component = comp
                        break

            if not component:
                continue

            # Get existing tests for this component
            existing_tests = self.db.query(ComponentTest).filter(
                ComponentTest.component_id == component.id
            ).all()
            existing_map = {(t.test_file, t.test_name): t for t in existing_tests}

            for test_info in tests:
                key = (test_info["test_file"], test_info["test_name"])
                if key not in existing_map:
                    # Create new test record
                    test = ComponentTest(
                        component_id=component.id,
                        test_file=test_info["test_file"],
                        test_name=test_info["test_name"],
                        test_type=test_info["test_type"],
                        generated_by="discovered",
                        last_status="pending"
                    )
                    self.db.add(test)
                    tests_synced += 1

            # Update component test count
            new_test_count = len(tests)
            if component.test_count != new_test_count:
                component.test_count = new_test_count
                components_updated += 1

        self.db.commit()
        return tests_synced, components_updated


# Singleton instance
_discovery_service = None


def get_discovery_service(db: Session = None) -> ComponentDiscoveryService:
    """Get component discovery service instance"""
    if db:
        return ComponentDiscoveryService(db)

    global _discovery_service
    if _discovery_service is None:
        from .database import SessionLocal
        _discovery_service = ComponentDiscoveryService(SessionLocal())
    return _discovery_service
