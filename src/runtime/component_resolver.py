"""
Quantum Component Resolver

Phase 2: Component Composition
Responsible for finding, loading, and caching imported components.
"""

import sys
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ComponentNode, ImportNode


@dataclass
class ComponentMetadata:
    """Metadata about a resolved component"""
    name: str
    path: Path
    ast: ComponentNode
    imports: List[ImportNode]


class ComponentResolver:
    """
    Resolves and loads Quantum components.

    Phase 2: Component Composition

    Responsibilities:
    - Find component .q files by name
    - Load and parse components
    - Cache parsed components
    - Resolve component dependencies
    """

    def __init__(self, components_dir: str = "./components"):
        self.components_dir = Path(components_dir)
        self.parser = QuantumParser()

        # Component cache: {name: ComponentMetadata}
        self.cache: Dict[str, ComponentMetadata] = {}

    def resolve(self, component_name: str, from_path: Optional[str] = None) -> ComponentMetadata:
        """
        Resolve component by name.

        Args:
            component_name: Name of component (e.g., "Header", "Button")
            from_path: Optional relative path (e.g., "./ui", "../shared")

        Returns:
            ComponentMetadata with AST and metadata

        Raises:
            ComponentNotFoundError: If component file doesn't exist
        """

        # Check cache first
        cache_key = f"{from_path or 'default'}:{component_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Find component file
        component_path = self._find_component_file(component_name, from_path)

        if not component_path.exists():
            raise ComponentNotFoundError(
                f"Component '{component_name}' not found. "
                f"Searched: {component_path}"
            )

        # Parse component
        try:
            ast = self.parser.parse_file(str(component_path))

            if not isinstance(ast, ComponentNode):
                raise ComponentNotFoundError(
                    f"File '{component_path}' is not a component "
                    f"(got {type(ast).__name__})"
                )

            # Extract imports from component
            imports = [stmt for stmt in ast.statements if isinstance(stmt, ImportNode)]

            # Create metadata
            metadata = ComponentMetadata(
                name=component_name,
                path=component_path,
                ast=ast,
                imports=imports
            )

            # Cache it
            self.cache[cache_key] = metadata

            return metadata

        except QuantumParseError as e:
            raise ComponentNotFoundError(
                f"Failed to parse component '{component_name}': {e}"
            )

    def _find_component_file(self, component_name: str, from_path: Optional[str] = None) -> Path:
        """
        Find component .q file.

        Resolution order:
        1. If from_path provided: {from_path}/{ComponentName}.q
        2. Default: {components_dir}/{ComponentName}.q
        3. Try lowercase: {components_dir}/{componentname}.q
        4. Try snake_case: {components_dir}/{component_name}.q
        """

        # Try from_path first if provided
        if from_path:
            from_dir = self.components_dir / from_path.lstrip('./')
            path = from_dir / f"{component_name}.q"
            if path.exists():
                return path

        # Try exact name
        path = self.components_dir / f"{component_name}.q"
        if path.exists():
            return path

        # Try lowercase
        path = self.components_dir / f"{component_name.lower()}.q"
        if path.exists():
            return path

        # Try snake_case conversion
        snake_case_name = self._to_snake_case(component_name)
        path = self.components_dir / f"{snake_case_name}.q"
        if path.exists():
            return path

        # Return original path (will trigger not found error)
        return self.components_dir / f"{component_name}.q"

    def _to_snake_case(self, name: str) -> str:
        """
        Convert PascalCase to snake_case.

        Examples:
          ProductCard → product_card
          AdminLayout → admin_layout
          UserProfileHeader → user_profile_header
        """
        import re
        # Insert underscore before uppercase letters
        result = re.sub(r'(?<!^)(?=[A-Z])', '_', name)
        return result.lower()

    def clear_cache(self):
        """Clear component cache (useful for development hot-reload)"""
        self.cache.clear()

    def preload(self, component_names: List[str]):
        """Preload components into cache"""
        for name in component_names:
            try:
                self.resolve(name)
            except ComponentNotFoundError:
                pass  # Skip missing components


class ComponentNotFoundError(Exception):
    """Component file not found or invalid"""
    pass
