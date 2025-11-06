"""
Module System - Multi-File MXML Application Support

Handles:
- Namespace resolution (xmlns:components="components.*")
- Dependency discovery (<components:UserCard/>)
- Recursive file parsing
- Dependency graph construction
- Compilation order (topological sort)
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Namespace:
    """Namespace declaration"""
    prefix: str              # "components"
    package: str             # "components.*"
    resolved_path: str       # "src/components/"


@dataclass
class Dependency:
    """File dependency"""
    source_file: str         # "Main.mxml"
    target_file: str         # "components/UserCard.mxml"
    component_name: str      # "UserCard"
    namespace_prefix: str    # "components"


@dataclass
class ModuleInfo:
    """Information about a parsed module"""
    file_path: str
    namespaces: Dict[str, Namespace]  # prefix → Namespace
    dependencies: List[Dependency]
    ast: any  # MXML AST


class DependencyGraph:
    """Dependency graph for compilation order"""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, Set[str]] = {}  # file → dependencies

    def add_node(self, file_path: str):
        """Add a file to the graph"""
        self.nodes.add(file_path)
        if file_path not in self.edges:
            self.edges[file_path] = set()

    def add_edge(self, from_file: str, to_file: str):
        """Add dependency: from_file depends on to_file"""
        self.add_node(from_file)
        self.add_node(to_file)
        self.edges[from_file].add(to_file)

    def topological_sort(self) -> List[str]:
        """
        Return compilation order (dependencies first)

        Uses Kahn's algorithm
        """
        # Calculate in-degree (how many files depend on this file)
        in_degree = {node: 0 for node in self.nodes}

        for node in self.nodes:
            for neighbor in self.edges[node]:
                in_degree[neighbor] += 1

        # Start with files that have no dependencies
        queue = [node for node in self.nodes if in_degree[node] == 0]
        result = []

        while queue:
            # Take a file with no dependencies
            current = queue.pop(0)
            result.append(current)

            # Remove this file from dependency list
            for neighbor in self.edges[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self.nodes):
            # Circular dependency detected
            raise ValueError("Circular dependency detected in modules")

        # Reverse: we want dependencies first
        return list(reversed(result))

    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get direct dependencies of a file"""
        return self.edges.get(file_path, set())


class ModuleResolver:
    """
    Resolve module paths from namespace imports

    Example:
    xmlns:components="components.*"
    <components:UserCard/>

    Resolves to: src/components/UserCard.mxml
    """

    def __init__(self, source_root: str = "src"):
        self.source_root = Path(source_root)

    def extract_namespaces(self, mxml_content: str) -> Dict[str, Namespace]:
        """
        Extract namespace declarations from MXML

        Example:
        <Application xmlns:components="components.*">

        Returns:
        {"components": Namespace(prefix="components", package="components.*", resolved_path="src/components/")}
        """
        namespaces = {}

        # Match xmlns:prefix="package"
        pattern = r'xmlns:(\w+)="([^"]+)"'

        for match in re.finditer(pattern, mxml_content):
            prefix = match.group(1)
            package = match.group(2)

            # Skip standard namespaces
            if prefix in ['fx', 's', 'mx', 'q']:
                continue

            # Resolve package path
            # "components.*" → "src/components/"
            # "screens.dashboard.*" → "src/screens/dashboard/"
            package_path = package.replace('.*', '').replace('.', '/')
            resolved_path = str(self.source_root / package_path)

            namespaces[prefix] = Namespace(
                prefix=prefix,
                package=package,
                resolved_path=resolved_path
            )

        return namespaces

    def extract_component_usage(self, mxml_content: str, namespaces: Dict[str, Namespace]) -> List[Tuple[str, str]]:
        """
        Extract custom component usage

        Example:
        <components:UserCard/>

        Returns:
        [("components", "UserCard")]
        """
        components = []

        # Match <prefix:ComponentName
        pattern = r'<(\w+):(\w+)'

        for match in re.finditer(pattern, mxml_content):
            prefix = match.group(1)
            component_name = match.group(2)

            # Skip standard namespaces
            if prefix in ['fx', 's', 'mx', 'q']:
                continue

            # Only include if namespace is declared
            if prefix in namespaces:
                components.append((prefix, component_name))

        return components

    def resolve_component_path(self, namespace_prefix: str, component_name: str, namespaces: Dict[str, Namespace]) -> Optional[str]:
        """
        Resolve component to file path

        Example:
        prefix="components", name="UserCard"

        Returns:
        "src/components/UserCard.mxml"
        """
        if namespace_prefix not in namespaces:
            return None

        namespace = namespaces[namespace_prefix]
        component_path = Path(namespace.resolved_path) / f"{component_name}.mxml"

        return str(component_path)


class ModuleSystem:
    """
    Multi-file MXML application support

    Handles recursive parsing and dependency resolution
    """

    def __init__(self, source_root: str = "src"):
        self.source_root = Path(source_root)
        self.resolver = ModuleResolver(source_root)
        self.modules: Dict[str, ModuleInfo] = {}  # file_path → ModuleInfo
        self.graph = DependencyGraph()

    def load_application(self, entry_file: str) -> List[ModuleInfo]:
        """
        Load application starting from entry file

        Returns list of all modules in compilation order
        """
        # Parse recursively
        self._parse_recursive(entry_file, set())

        # Get compilation order
        compile_order = self.graph.topological_sort()

        # Return modules in order
        return [self.modules[f] for f in compile_order]

    def _parse_recursive(self, file_path: str, visited: Set[str]):
        """Recursively parse file and its dependencies"""

        # Normalize path
        file_path = str(Path(file_path))

        if file_path in visited:
            return

        visited.add(file_path)

        # Check if file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"MXML file not found: {file_path}")

        # Read file
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract namespaces
        namespaces = self.resolver.extract_namespaces(content)

        # Extract component usage
        component_usage = self.resolver.extract_component_usage(content, namespaces)

        # Resolve dependencies
        dependencies = []
        for prefix, component_name in component_usage:
            dep_path = self.resolver.resolve_component_path(prefix, component_name, namespaces)

            if dep_path:
                dependencies.append(Dependency(
                    source_file=file_path,
                    target_file=dep_path,
                    component_name=component_name,
                    namespace_prefix=prefix
                ))

                # Add to graph
                self.graph.add_edge(file_path, dep_path)

                # Parse dependency
                self._parse_recursive(dep_path, visited)

        # Parse MXML (using existing parser)
        from .mxml_parser import MXMLParser
        parser = MXMLParser()
        ast = parser.parse(file_path)

        # Store module info
        self.modules[file_path] = ModuleInfo(
            file_path=file_path,
            namespaces=namespaces,
            dependencies=dependencies,
            ast=ast
        )

    def get_compilation_order(self) -> List[str]:
        """Get files in compilation order (dependencies first)"""
        return self.graph.topological_sort()

    def get_module(self, file_path: str) -> Optional[ModuleInfo]:
        """Get module info by file path"""
        return self.modules.get(file_path)

    def get_all_modules(self) -> List[ModuleInfo]:
        """Get all loaded modules"""
        return list(self.modules.values())


# Example usage
if __name__ == '__main__':
    # Create example files
    import tempfile
    import os

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    src_dir = os.path.join(temp_dir, 'src')
    components_dir = os.path.join(src_dir, 'components')
    os.makedirs(components_dir)

    # Main.mxml
    main_content = '''<?xml version="1.0"?>
<Application
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark"
    xmlns:components="components.*">

    <s:VBox>
        <components:UserCard/>
    </s:VBox>
</Application>
'''

    # components/UserCard.mxml
    usercard_content = '''<?xml version="1.0"?>
<Component
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark">

    <s:VBox>
        <s:Label text="User Card"/>
    </s:VBox>
</Component>
'''

    # Write files
    main_file = os.path.join(src_dir, 'Main.mxml')
    usercard_file = os.path.join(components_dir, 'UserCard.mxml')

    with open(main_file, 'w') as f:
        f.write(main_content)

    with open(usercard_file, 'w') as f:
        f.write(usercard_content)

    # Test module system
    module_system = ModuleSystem(source_root=src_dir)

    try:
        modules = module_system.load_application(main_file)

        print(f"Loaded {len(modules)} modules:")
        for module in modules:
            print(f"  - {module.file_path}")

        print(f"\nCompilation order:")
        for file in module_system.get_compilation_order():
            print(f"  {file}")

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
